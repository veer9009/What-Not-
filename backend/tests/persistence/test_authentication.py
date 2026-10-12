import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.dependencies import get_session, get_transaction_session
from app.core.config import Settings
from app.main import create_app
from app.models import User, SellerProfile

PASSWORD = ' ' + secrets.token_urlsafe(24) + ' '
SECRET = 'isolated-test-key-only-' + 'x' * 40
REGISTRATION = dict(name='Ravi', email='Ravi@Example.com', phone='9000000001',
                    password=PASSWORD, role='SELLER')


@pytest.fixture
def auth_client(db):
    app = create_app(Settings(_env_file=None, environment='test', jwt_secret_key=SECRET))
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_transaction_session] = lambda: db
    with TestClient(app) as client:
        yield client


def register(client, **changes):
    return client.post('/api/v1/auth/register', json={**REGISTRATION, **changes})


def login(client, email='ravi@example.com', password=PASSWORD):
    return client.post('/api/v1/auth/login', json=dict(email=email, password=password))


@pytest.mark.parametrize('role', ['BUYER', 'SELLER'])
def test_registration_hashes_password_normalizes_identity_and_creates_only_user(auth_client, db, role):
    response = register(auth_client, role=role, phone=' 9000000001 ')
    assert response.status_code == 201
    assert response.json()['email'] == 'ravi@example.com'
    assert response.json()['role'] == role
    assert set(response.json()) == {'id', 'name', 'email', 'role'}
    user = db.scalar(select(User))
    assert user.phone == '9000000001'
    assert user.password_hash.startswith('$argon2id$')
    assert PASSWORD not in user.password_hash
    assert db.scalar(select(SellerProfile)) is None
    # Exact password must be preserved, including its trailing space.
    assert login(auth_client).status_code == 200
    assert login(auth_client, password=PASSWORD.rstrip()).status_code == 401


@pytest.mark.parametrize('changes', [dict(email='RAVI@example.com', phone='different'),
                                     dict(email='other@example.com')])
def test_duplicate_registration_returns_conflict(auth_client, changes):
    assert register(auth_client).status_code == 201
    response = register(auth_client, **changes)
    assert response.status_code == 409
    assert 'password' not in response.text


@pytest.mark.parametrize('changes', [dict(role='ADMIN'), dict(role='ROOT'), dict(is_active=True),
    dict(id=12), dict(password_hash='a secret hash'), dict(phone=' '), dict(phone='x' * 33),
    dict(password=secrets.token_hex(2)), dict(password='x' * 129), dict(name=' '), dict(email='invalid')])
def test_registration_validation_is_safe_and_prevents_privilege_escalation(auth_client, changes):
    response = register(auth_client, **changes)
    assert response.status_code == 422
    assert PASSWORD not in response.text
    assert 'a secret hash' not in response.text
    assert all('input' not in error for error in response.json()['detail'])


def test_login_token_and_me_are_safe(auth_client):
    assert register(auth_client).status_code == 201
    response = login(auth_client)
    assert response.status_code == 200
    data = response.json()
    assert data['token_type'] == 'bearer'
    assert data['expires_in'] == 900
    assert 'password' not in response.text
    token = data['access_token']
    me = auth_client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200
    assert me.json() == data['user']
    assert response.headers['cache-control'] == 'no-store'


def test_bad_unknown_and_inactive_credentials_share_401(auth_client, db):
    register(auth_client)
    wrong = login(auth_client, password=PASSWORD + secrets.token_hex(2))
    unknown = login(auth_client, email='absent@example.com')
    user = db.scalar(select(User))
    user.is_active = False
    db.flush()
    inactive = login(auth_client)
    assert wrong.status_code == unknown.status_code == inactive.status_code == 401
    assert wrong.json() == unknown.json() == inactive.json()
    assert wrong.headers['www-authenticate'] == 'Bearer'


def test_inactive_and_deleted_users_lose_token_access(auth_client, db):
    register(auth_client)
    token = login(auth_client).json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    user = db.scalar(select(User))
    user.is_active = False
    db.flush()
    assert auth_client.get('/api/v1/auth/me', headers=headers).status_code == 401
    db.delete(user)
    db.flush()
    assert auth_client.get('/api/v1/auth/me', headers=headers).status_code == 401


@pytest.mark.parametrize('authorization', [None, 'Bearer nonsense', 'Basic xyz', 'Bearer'])
def test_missing_and_malformed_authentication_rejected_without_storage(client, authorization):
    headers = {} if authorization is None else {'Authorization': authorization}
    response = client.get('/api/v1/auth/me', headers=headers)
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'
    assert client.app.state.database_engine is None


def test_legacy_case_variant_login_and_ambiguous_identity_fail_closed(auth_client, db):
    from app.core.security import hash_password
    encoded = hash_password(PASSWORD)
    first = User(name='Legacy', email='Legacy@example.com', phone='legacy1',
                 password_hash=encoded, role='BUYER')
    db.add(first)
    db.flush()
    assert login(auth_client, email='LEGACY@example.com').status_code == 200
    assert register(auth_client, email='legacy@example.com').status_code == 409
    db.add(User(name='Collision', email='legacy@example.com', phone='legacy2',
                password_hash=encoded, role='ADMIN'))
    db.flush()
    assert login(auth_client, email='legacy@example.com').status_code == 401


def test_bcrypt_login_upgrades_hash_and_invalid_stored_hash_fails(auth_client, db):
    import bcrypt
    user = User(name='Legacy', email='legacy@example.com', phone='legacy', role='BUYER',
                password_hash=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode())
    db.add(user)
    db.flush()
    assert login(auth_client, email=user.email).status_code == 200
    assert user.password_hash.startswith('$argon2id$')
    user.password_hash = 'invalid stored hash'
    db.flush()
    assert login(auth_client, email=user.email).status_code == 401


def test_independent_salts_for_identical_passwords(auth_client, db):
    register(auth_client)
    register(auth_client, email='second@example.com', phone='second')
    hashes = list(db.scalars(select(User.password_hash).order_by(User.id)))
    assert len(hashes) == 2 and hashes[0] != hashes[1]


@pytest.mark.parametrize('password', [secrets.token_hex(4), secrets.token_hex(64), chr(0x5BC6) * 128])
def test_password_boundaries_support_unicode(auth_client, password):
    assert register(auth_client, password=password).status_code == 201
    assert login(auth_client, password=password).status_code == 200


def test_valid_token_with_missing_secret_fails_closed_without_storage(client):
    import time
    import jwt
    token = jwt.encode(dict(sub='1', iat=int(time.time()), exp=int(time.time()) + 900), SECRET, algorithm='HS256')
    response = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 503
    assert client.app.state.database_engine is None
