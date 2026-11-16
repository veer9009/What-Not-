"""Real HTTP + PostgreSQL transactions; all identities live in a disposable schema."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import uuid4
from threading import Barrier

from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.core.config import Settings
from app.core.security import hash_password
from app.main import create_app
from app.models import User

ORIGIN='https://testserver'
CSRF={'Origin':ORIGIN,'X-WhatNot-CSRF':'1'}
PASSWORD='Synthetic only session test password'


@pytest.fixture(scope='session')
def encoded_password():
    return hash_password(PASSWORD)


@pytest.fixture
def system(session_engine,encoded_password):
    settings=Settings(_env_file=None,environment='test',jwt_secret_key=secrets.token_urlsafe(48),
                      abuse_limits_enabled=False,cors_origins=[ORIGIN])
    app=create_app(settings)
    def reader():
        with Session(session_engine) as session:
            yield session
    app.dependency_overrides[get_session]=reader
    actors={}
    with Session(session_engine) as session, session.begin():
        for role in ('BUYER','SELLER','ADMIN'):
            user=User(name='Synthetic '+role,email=f'{uuid4().hex}@example.com',phone=uuid4().hex,
                      password_hash=encoded_password,role=role)
            session.add(user);session.flush();actors[role]={'id':user.id,'email':user.email}
    with TestClient(app,base_url=ORIGIN) as client:
        yield client,session_engine,settings,actors,app


def login(system,role='SELLER'):
    client,engine,settings,actors,app=system
    response=client.post('/api/v1/auth/login',headers=CSRF,
                         json={'email':actors[role]['email'],'password':PASSWORD})
    assert response.status_code==200
    return response


def access(response):
    return {'Authorization':'Bearer '+response.json()['access_token']}


def test_postgresql_non_utc_expiry_serializes_same_instant_as_gmt(system):
    from email.utils import parsedate_to_datetime
    client, engine, settings, actors, app = system
    login(system)
    with engine.connect() as connection:
        expiry = connection.execute(text('SELECT expires_at FROM auth_sessions WHERE user_id=:id'),
                                    {'id': actors['SELLER']['id']}).scalar_one()
    assert expiry.utcoffset() == timedelta(hours=5, minutes=30)
    response = client.post('/api/v1/auth/refresh', headers=CSRF)
    assert response.status_code == 200
    from http.cookies import SimpleCookie
    cookie = SimpleCookie(response.headers['set-cookie'])
    serialized = parsedate_to_datetime(cookie['wn_refresh']['expires'])
    assert serialized.utcoffset() == timedelta(0)
    assert serialized == expiry.replace(microsecond=0)


def test_login_cookie_hash_rotation_and_logout_revoke_access(system):
    client,engine,*_=system
    response=login(system)
    cookie=response.headers['set-cookie']
    assert all(flag in cookie.lower() for flag in ['httponly','secure','samesite=strict','path=/api/v1/auth'])
    assert response.json()['expires_in']==900
    first=client.cookies.get('wn_refresh')
    assert first and first not in response.text
    assert client.get('/api/v1/auth/me',headers=access(response)).status_code==200
    rotated=client.post('/api/v1/auth/refresh',headers=CSRF)
    assert rotated.status_code==200
    second=client.cookies.get('wn_refresh')
    assert first!=second
    with engine.connect() as connection:
        rows=connection.execute(text('SELECT digest FROM auth_refresh_tokens')).scalars().all()
        assert hashlib.sha256(first.encode()).hexdigest() in rows
        assert first not in rows and second not in rows
    assert client.post('/api/v1/auth/logout',headers=CSRF).status_code in {200,204}
    assert client.get('/api/v1/auth/me',headers=access(rotated)).status_code==401
    assert client.post('/api/v1/auth/refresh',headers=CSRF).status_code==401


def test_used_refresh_replay_revokes_family_and_latest_access(system):
    client,*_=system
    login(system);stolen=client.cookies.get('wn_refresh')
    renewed=client.post('/api/v1/auth/refresh',headers=CSRF)
    assert renewed.status_code==200
    current=client.cookies.get('wn_refresh')
    client.cookies.clear();client.cookies.set('wn_refresh',stolen,domain='testserver.local',path='/api/v1/auth')
    assert client.post('/api/v1/auth/refresh',headers=CSRF).status_code==401
    assert client.get('/api/v1/auth/me',headers=access(renewed)).status_code==401
    client.cookies.clear();client.cookies.set('wn_refresh',current,domain='testserver.local',path='/api/v1/auth')
    assert client.post('/api/v1/auth/refresh',headers=CSRF).status_code==401


@pytest.mark.parametrize('role,hours',[('BUYER',8),('SELLER',8),('ADMIN',.25)])
def test_absolute_role_session_ceiling_and_no_sliding_extension(system,role,hours):
    client,engine,settings,actors,app=system
    response=login(system,role)
    with engine.connect() as connection:
        row=connection.execute(text('SELECT created_at,expires_at FROM auth_sessions WHERE user_id=:id'),{'id':actors[role]['id']}).one()
    assert (row.expires_at-row.created_at).total_seconds()==pytest.approx(hours*3600,abs=1)
    assert client.post('/api/v1/auth/refresh',headers=CSRF).status_code==200
    with engine.connect() as connection:
        assert connection.execute(text('SELECT expires_at FROM auth_sessions WHERE user_id=:id'),{'id':actors[role]['id']}).scalar_one()==row.expires_at


@pytest.mark.parametrize('headers',[{}, {'Origin':'https://evil.example','X-WhatNot-CSRF':'1'},
    {'Origin':ORIGIN}, {**CSRF,'Sec-Fetch-Site':'cross-site'}])
def test_cookie_mutations_require_csrf_origin_and_custom_header(system,headers):
    client,*_=system
    original=login(system);cookie=client.cookies.get('wn_refresh')
    for endpoint in ('refresh','logout'):
        assert client.post('/api/v1/auth/'+endpoint,headers=headers).status_code==403
    assert client.cookies.get('wn_refresh')==cookie
    assert client.get('/api/v1/auth/me',headers=access(original)).status_code==200


def test_suspension_and_current_database_role_enforced(system):
    client,engine,settings,actors,app=system
    response=login(system)
    with engine.begin() as connection:
        connection.execute(text("UPDATE users SET role='BUYER' WHERE id=:id"),{'id':actors['SELLER']['id']})
    # A role change invalidates the old session, including privilege increases.
    assert client.get('/api/v1/auth/me',headers=access(response)).status_code==401
    assert client.get('/api/v1/sellers/me',headers=access(response)).status_code==401
    with engine.begin() as connection:
        connection.execute(text('UPDATE users SET is_active=false WHERE id=:id'),{'id':actors['SELLER']['id']})
    assert client.get('/api/v1/auth/me',headers=access(response)).status_code==401
    assert client.post('/api/v1/auth/refresh',headers=CSRF).status_code==401


def test_expired_session_rejects_access_and_refresh(system):
    client,engine,settings,actors,app=system
    response=login(system)
    with engine.begin() as connection:
        connection.execute(text("UPDATE auth_sessions SET expires_at=now()-interval '1 second' WHERE user_id=:id"),{'id':actors['SELLER']['id']})
    assert client.get('/api/v1/auth/me',headers=access(response)).status_code==401
    assert client.post('/api/v1/auth/refresh',headers=CSRF).status_code==401


def test_two_concurrent_uses_rotate_once_and_replay_revokes_family(system):
    client,engine,settings,actors,app=system
    login(system);raw=client.cookies.get('wn_refresh')
    barrier=Barrier(2)
    def rotate():
        with TestClient(app,base_url=ORIGIN) as browser:
            barrier.wait(timeout=10)
            return browser.post('/api/v1/auth/refresh',headers={**CSRF,'Cookie':'wn_refresh='+raw})
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(rotate) for _ in range(2)]
        responses=[future.result(timeout=30) for future in futures]
    assert sorted(response.status_code for response in responses)==[200,401]
    winner=next(response for response in responses if response.status_code==200)
    assert client.get('/api/v1/auth/me',headers=access(winner)).status_code==401


def test_login_csrf_rejection_does_not_replace_existing_session(system):
    client,engine,settings,actors,app=system
    original=login(system)
    cookie=client.cookies.get('wn_refresh')
    result=client.post('/api/v1/auth/login',headers={'Origin':'https://evil.example','X-WhatNot-CSRF':'1'},
        json={'email':actors['BUYER']['email'],'password':PASSWORD})
    assert result.status_code==403
    assert client.cookies.get('wn_refresh')==cookie
    assert client.get('/api/v1/auth/me',headers=access(original)).status_code==200


def test_refresh_cookie_never_authenticates_bearer_routes_by_itself(system):
    client,*_=system
    login(system)
    # The API boundary requires an access JWT, not just a cookie.
    assert client.get('/api/v1/auth/me').status_code==401


def test_explicit_server_revocation_rejects_access_and_refresh(system):
    client,engine,settings,actors,app=system
    response=login(system)
    with engine.begin() as connection:
        connection.execute(text('UPDATE auth_sessions SET revoked_at=now() WHERE user_id=:id'),{'id':actors['SELLER']['id']})
    assert client.get('/api/v1/auth/me',headers=access(response)).status_code==401
    assert client.post('/api/v1/auth/refresh',headers=CSRF).status_code==401


def test_cors_credentials_only_for_explicit_origin(system):
    client,*_=system
    headers={'Origin':ORIGIN,'Access-Control-Request-Method':'POST',
             'Access-Control-Request-Headers':'X-WhatNot-CSRF,Content-Type'}
    result=client.options('/api/v1/auth/refresh',headers=headers)
    assert result.status_code==200
    assert result.headers['access-control-allow-origin']==ORIGIN
    assert result.headers['access-control-allow-credentials']=='true'
    result=client.options('/api/v1/auth/refresh',headers={**headers,'Origin':'https://evil.example'})
    assert 'access-control-allow-origin' not in result.headers


def test_expired_access_renews_only_with_cookie_and_legacy_bearer_is_rejected(system):
    client,engine,settings,actors,app=system
    response=login(system)
    claims=jwt.decode(response.json()['access_token'],settings.jwt_secret_key.get_secret_value(),algorithms=['HS256'])
    claims.update(iat=int(datetime.now(timezone.utc).timestamp())-1000,exp=int(datetime.now(timezone.utc).timestamp())-10)
    expired=jwt.encode(claims,settings.jwt_secret_key.get_secret_value(),algorithm='HS256')
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+expired}).status_code==401
    assert client.post('/api/v1/auth/refresh',headers=CSRF).status_code==200
    del claims['sid'];claims.update(iat=int(datetime.now(timezone.utc).timestamp()),exp=int(datetime.now(timezone.utc).timestamp())+900)
    legacy=jwt.encode(claims,settings.jwt_secret_key.get_secret_value(),algorithm='HS256')
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+legacy}).status_code==401


def test_order_action_and_confirmed_delivery_ownership_survive_renewal(system, encoded_password):
    from app.models import Address, Order, OrderItem, Product, SellerProfile
    client, engine, settings, actors, app = system
    with Session(engine) as session, session.begin():
        shop = SellerProfile(user_id=actors['SELLER']['id'], shop_name='Synthetic shop',
                             phone=uuid4().hex, latitude='0', longitude='0')
        address = Address(user_id=actors['BUYER']['id'], label='Test', address_line1='Synthetic address',
                          city='Test city', state='Test state', pincode='400001', latitude='0', longitude='0')
        stranger = User(name='Other synthetic seller', email=f'{uuid4().hex}@example.com',
                        phone=uuid4().hex, role='SELLER', password_hash=encoded_password)
        session.add_all([shop, address, stranger]); session.flush()
        product = Product(seller_id=shop.id, name='Synthetic item', description='Test item',
                          price='1', stock_quantity=5, category='Crafts', delivery_radius_km=2)
        order = Order(buyer_id=actors['BUYER']['id'], seller_id=shop.id, address_id=address.id,
                      subtotal='1', delivery_fee='0', total_amount='1')
        session.add_all([product, order]); session.flush()
        session.add(OrderItem(order_id=order.id, product_id=product.id, seller_id=shop.id,
                              product_name=product.name, quantity=1, unit_price='1'))
        order_id, stranger_email = order.id, stranger.email
    buyer = login(system, 'BUYER')
    path = f'/api/v1/orders/{order_id}'
    assert client.post(path+'/delivery-location-confirmation', headers=access(buyer),
                       json={'latitude':'0', 'longitude':'0'}).status_code == 200
    login(system, 'SELLER')
    renewed = client.post('/api/v1/auth/refresh', headers=CSRF)
    assert renewed.status_code == 200
    assert client.patch(path+'/status', headers=access(renewed), json={'status':'ACCEPTED'}).status_code == 200
    fulfillment = client.get(path+'/fulfillment', headers=access(renewed))
    assert fulfillment.status_code == 200
    assert fulfillment.json()['delivery_location_confirmed'] is True
    assert 'latitude' not in client.get(path, headers=access(renewed)).text
    other = client.post('/api/v1/auth/login', headers=CSRF, json={'email':stranger_email,'password':PASSWORD})
    assert other.status_code == 200
    assert client.get(path+'/fulfillment', headers=access(other)).status_code == 403
    admin = login(system, 'ADMIN')
    assert client.get(path, headers=access(admin)).status_code == 403
