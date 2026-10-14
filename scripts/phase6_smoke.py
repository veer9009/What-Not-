"""Live browser smoke test using the existing isolated PostgreSQL harness only.

Run with backend/.venv Python. Requires a locally installed Playwright module
(WHATNOT_PLAYWRIGHT_MODULE) and browser (WHATNOT_BROWSER_EXECUTABLE optional).
Only the generated test DATABASE_URL is used. No credential artifacts are written.
"""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.security import hash_password
from app.services.inputs import UserCreate
from app.services.users import UserService


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def ready(url, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Owned test server exited before startup')
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(.1)
    raise RuntimeError('Owned test server did not become ready')


def main():
    if not os.environ.get('WHATNOT_PLAYWRIGHT_MODULE'):
        raise SystemExit('Set WHATNOT_PLAYWRIGHT_MODULE to an installed Playwright module')
    spec = importlib.util.spec_from_file_location('phase6_isolated_harness', BACKEND / 'tests/persistence/conftest.py')
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    cluster = harness.isolated_cluster.__wrapped__()
    processes = []
    try:
        connection = next(cluster)
        url = harness.fresh_database_url.__wrapped__(connection)
        assert url.database.startswith('whatnot_test_')
        assert url.database not in {'whatnot_db', 'upsc_compass'}
        command.upgrade(harness.migration_config(url), 'head')
        admin_password = secrets.token_urlsafe(24)
        engine = create_engine(url)
        try:
            with Session(engine) as session, session.begin():
                UserService(session).create(UserCreate(name='Test administrator', email='admin.phase6@example.com', phone='phase6-admin', password_hash=hash_password(admin_password), role='ADMIN'))
        finally:
            engine.dispose()
        api_port, ui_port = free_port(), free_port()
        while ui_port == api_port:
            ui_port = free_port()
        env = os.environ.copy()
        # Explicit values override all possible application settings; the app is
        # constructed with _env_file=None in the owned server subprocess below.
        env['DATABASE_URL'] = url.render_as_string(hide_password=False)
        env['WHAT_NOT_JWT_SECRET_KEY'] = secrets.token_urlsafe(48)
        env['WHAT_NOT_ENVIRONMENT'] = 'test'
        env['WHAT_NOT_JWT_ALGORITHM'] = 'HS256'
        env['WHAT_NOT_ACCESS_TOKEN_EXPIRE_MINUTES'] = '15'
        env['WHAT_NOT_CORS_ORIGINS'] = json.dumps([f'http://127.0.0.1:{ui_port}'])
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        with (ROOT / 'phase6-browser-servers.log').open('w', encoding='utf-8') as log:
            server_code = 'from app.main import create_app; from app.core.config import Settings; import uvicorn; uvicorn.run(create_app(Settings(_env_file=None)),host="127.0.0.1",port=' + str(api_port) + ',access_log=False)'
            processes.append(subprocess.Popen([sys.executable, '-c', server_code], cwd=BACKEND, env=env, stdout=log, stderr=log, creationflags=flags))
            processes.append(subprocess.Popen(['node', str(ROOT / 'node_modules/vite/bin/vite.js'), 'preview', '--host', '127.0.0.1', '--port', str(ui_port), '--strictPort'], cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=flags))
            ready(f'http://127.0.0.1:{api_port}/api/v1/health', processes[0])
            ready(f'http://127.0.0.1:{ui_port}', processes[1])
            data = {'ui': f'http://127.0.0.1:{ui_port}', 'api': f'http://127.0.0.1:{api_port}', 'password': secrets.token_urlsafe(24), 'adminPassword': admin_password}
            # Credentials go through an anonymous pipe, never a file/URL/argv.
            result = subprocess.run(['node', str(ROOT / 'scripts/phase6_browser.mjs')], input=json.dumps(data), text=True, cwd=ROOT, env=env, creationflags=flags, capture_output=True, timeout=180)
            if result.returncode != 0:
                raise RuntimeError('Live browser smoke failed. Raw browser failure output was discarded to keep credentials out of log artifacts.')
            print('Live isolated-backend browser smoke passed; 7 screens x 3 viewports, primary-button contrast >= 4.5, no horizontal page overflow, no geographic discovery or checkout requests.')
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        cluster.close()


if __name__ == '__main__':
    main()
