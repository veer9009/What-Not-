"""Non-destructive local audit probes; no database or network connections.

Run from root: backend/.venv/Scripts/python.exe docs/security/audit_runtime.py
Outputs observations, not assertions of production security.
"""
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import jwt
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app.api.dependencies import get_session
from app.core.config import Settings
from app.main import create_app


def main():
    key = secrets.token_urlsafe(48)
    production = dict(_env_file=None, environment='production',
                      database_url='postgresql+psycopg://synthetic@127.0.0.1:1/unit_probe',
                      trusted_hosts=['pilot.example.test'], cors_origins=['https://pilot.example.test'],
                      jwt_secret_key=key, beta_allowed_emails=['audit@example.com'])
    settings = Settings(**production)
    app = create_app(settings)
    def accepted(**changes):
        try:
            Settings(**(production | changes))
            return True
        except ValidationError:
            return False
    print('production_without_database_accepted', accepted(database_url=None))
    print('production_http_cors_accepted', accepted(cors_origins=['http://example.com']))
    print('production_smtp_without_tls_accepted', accepted(email_provider='smtp',
          smtp_host='smtp.example.test', email_from='audit@example.com',
          smtp_starttls=False, smtp_username='synthetic', smtp_password='synthetic'))
    try:
        Settings(**dict(production, jwt_secret_key=None))
        print('missing_production_key_rejected', False)
    except ValidationError:
        print('missing_production_key_rejected', True)

    # An unbound session cannot read/write any database. Missing/invalid bearer
    # credentials must be rejected before a business query is attempted.
    def isolated_session():
        with Session() as session:
            yield session
    app.dependency_overrides[get_session] = isolated_session
    now = int(datetime.now(timezone.utc).timestamp())
    expired = jwt.encode({'sub': '1', 'iat': now - 120, 'exp': now - 60}, key, algorithm='HS256')
    forged = jwt.encode({'sub': '1', 'iat': now, 'exp': now + 60}, secrets.token_urlsafe(48), algorithm='HS256')
    with TestClient(app, base_url='https://pilot.example.test', raise_server_exceptions=False) as client:
        for path in ['/api/v1/health', '/docs', '/redoc', '/openapi.json', '/.env', '/.git/config']:
            response = client.get(path)
            print('HTTP', path, response.status_code)
        response = client.get('/api/v1/health')
        print('HEADERS', json.dumps({h: response.headers.get(h) for h in [
            'cache-control', 'content-security-policy', 'strict-transport-security',
            'x-content-type-options', 'referrer-policy', 'x-frame-options', 'x-request-id']}))
        for kind, token in [('missing', None), ('malformed', 'invalid'), ('expired', expired), ('forged', forged)]:
            response = client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token} if token else {})
            print('TOKEN', kind, response.status_code)
        allowed = client.options('/api/v1/auth/me', headers={'Origin': 'https://pilot.example.test', 'Access-Control-Request-Method': 'GET'})
        denied = client.options('/api/v1/auth/me', headers={'Origin': 'https://evil.example', 'Access-Control-Request-Method': 'GET'})
        print('CORS', 'configured', allowed.status_code, 'unconfigured', denied.status_code,
              'unconfigured_acao', denied.headers.get('access-control-allow-origin'))

    # Build a complete source inventory, including routes hidden behind lazily
    # included FastAPI router wrappers. This avoids relying on app.routes alone.
    inventory = []
    aliases = {'CurrentUser', 'Buyer', 'Seller', 'Admin', 'OrderActor'}
    for path in sorted((ROOT / 'backend/app/api/routes').glob('*.py')):
        tree = ast.parse(path.read_text())
        prefix = ''
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == 'APIRouter':
                    prefix = next((kw.value.value for kw in node.value.keywords if kw.arg == 'prefix'), '')
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            role = next((arg.annotation.id for arg in node.args.args
                         if isinstance(arg.annotation, ast.Name) and arg.annotation.id in aliases), 'Public')
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in {'get', 'post', 'patch', 'delete', 'put'}:
                    route = '/api/v1' + prefix + dec.args[0].value
                    entry = dict(method=dec.func.attr.upper(), path=route, role=role,
                                 file=path.relative_to(ROOT).as_posix(), line=node.lineno)
                    if role != 'Public':
                        target = __import__('re').sub(r'\{[^}]+\}', '1', route)
                        with TestClient(app, base_url='https://pilot.example.test', raise_server_exceptions=False) as client:
                            entry['missing_token_status'] = client.request(entry['method'], target, json={}).status_code
                    inventory.append(entry)
    print('ROUTES', json.dumps(inventory))


if __name__ == '__main__':
    main()
