"""Exercise authentication and order GETs on PostgreSQL without changing records."""
import json
from pathlib import Path
import secrets
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.api.dependencies import get_session
from app.core.config import Settings
from app.core.security import create_access_token
from app.main import create_app

def verify():
    source = Settings()
    url = make_url(source.database_url.get_secret_value())
    assert url.host in {'localhost','127.0.0.1','::1'} and url.database.startswith('whatnot_') and not url.query
    engine = create_engine(url, hide_parameters=True, connect_args={'connect_timeout':5,
        'options':'-c default_transaction_read_only=on -c statement_timeout=5000'})
    try:
        with engine.connect() as connection:
            assert connection.scalar(text('SHOW transaction_read_only')) == 'on'
            assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0009'
            users = connection.execute(text('SELECT id,role,is_active FROM users ORDER BY id')).mappings().all()
            orders = connection.execute(text('SELECT o.id,o.buyer_id,s.user_id AS seller_user_id,o.status FROM orders o JOIN seller_profiles s ON s.id=o.seller_id')).mappings().all()
        # Test-only signer: no application secret or real account credential is emitted/changed.
        settings = Settings(_env_file=None, environment='test', database_url=None,
            jwt_secret_key=secrets.token_urlsafe(48), abuse_limits_enabled=False)
        app = create_app(settings)
        def reader():
            with Session(engine) as session:
                yield session
        app.dependency_overrides[get_session] = reader
        def bearer(user_id):
            return {'Authorization':'Bearer '+create_access_token(user_id,settings)}
        auth_checks = order_checks = denied_checks = 0
        active = {user['id']:user for user in users if user['is_active']}
        allowed = {'ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','DELIVERY_DISPUTED'}
        with TestClient(app) as client:
            for user in users:
                response = client.get('/api/v1/auth/me',headers=bearer(user['id']))
                assert response.status_code == (200 if user['is_active'] else 401)
                if user['is_active']:
                    assert response.json()['role'] == user['role']
                auth_checks += 1
            assert client.get('/api/v1/auth/me').status_code == 401
            now = int(time.time())
            expired = jwt.encode({'sub':str(next(iter(active))), 'iat':now-1000, 'exp':now-100},
                settings.jwt_secret_key.get_secret_value(), algorithm='HS256')
            assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+expired}).status_code == 401
            assert client.post('/api/v1/auth/refresh',json={}).status_code == 404
            assert client.post('/api/v1/auth/logout',json={}).status_code == 404
            for order in orders:
                path = f"/api/v1/orders/{order['id']}"
                assert client.get(path+'/fulfillment').status_code == 401
                for user_id,user in active.items():
                    if user['role']=='ADMIN':
                        # Administrator fulfillment reads write an audit event and are outside this read-only test.
                        continue
                    response = client.get(path+'/fulfillment',headers=bearer(user_id))
                    owner_buyer = user['role']=='BUYER' and user_id==order['buyer_id']
                    owner_seller = user['role']=='SELLER' and user_id==order['seller_user_id']
                    permitted = owner_buyer or (owner_seller and order['status'] in allowed)
                    assert response.status_code == (200 if permitted else 403)
                    if permitted:
                        data = response.json()
                        assert response.headers['cache-control']=='no-store'
                        if owner_seller and not data['delivery_location_confirmed']:
                            assert data['delivery_location'] is None
                        public = client.get(path,headers=bearer(user_id))
                        assert public.status_code==200
                        assert 'latitude' not in public.text and 'longitude' not in public.text
                    else:
                        denied_checks += 1
                    order_checks += 1
        with engine.connect() as connection:
            assert connection.scalar(text('SHOW transaction_read_only')) == 'on'
        return {'database':url.database,'read_only':True,'identity_checks':auth_checks,
            'order_fulfillment_checks':order_checks,'denied_order_reads':denied_checks,
            'expired_token_rejected':True,'anonymous_rejected':True,
            'refresh_endpoint_present':False,'server_logout_endpoint_present':False,
            'coordinates_recorded':False,'records_changed':False,'migrations_executed':False}
    finally:
        engine.dispose()

if __name__=='__main__':
    try:
        report=json.dumps(verify(),indent=2)
    except Exception as error:
        print(json.dumps({'error_class':type(error).__name__,'private_details_suppressed':True}))
        raise SystemExit(1)
    (Path(__file__).parent/'evidence/navigation-session-readonly.json').write_text(report,encoding='utf-8')
    print(report)
