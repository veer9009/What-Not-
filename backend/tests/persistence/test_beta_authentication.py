"""Admission and session contract over real HTTP and disposable PostgreSQL data."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.models import User
from test_authentication import auth_client, register, login, SECRET


@pytest.fixture
def admitted(auth_client):
    # Validate configuration as startup does, rather than assigning mixed-case
    # entries to an already initialized model.
    auth_client.app.state.settings = Settings(_env_file=None, environment='test',
        jwt_secret_key=SECRET, beta_allowed_emails=['RAVI@Example.com'])
    return auth_client


@pytest.mark.parametrize('role', ['BUYER', 'SELLER'])
def test_admitted_registration_login_refresh_roles_and_logout(admitted, role):
    registered = register(admitted, role=role)
    assert registered.status_code == 201
    assert registered.json()['role'] == role
    signed_in = login(admitted, email='RAVI@EXAMPLE.COM')
    assert signed_in.status_code == 200
    first_cookie = admitted.cookies.get('wn_refresh')
    assert first_cookie
    cookie_header = signed_in.headers['set-cookie']
    assert all(flag in cookie_header for flag in ('Secure', 'HttpOnly', 'SameSite=strict'))
    renewed = admitted.post('/api/v1/auth/refresh')
    assert renewed.status_code == 200
    assert admitted.cookies.get('wn_refresh') != first_cookie
    headers = {'Authorization': 'Bearer ' + renewed.json()['access_token']}
    me = admitted.get('/api/v1/auth/me', headers=headers)
    assert me.status_code == 200
    assert me.json() == registered.json()
    assert admitted.get('/api/v1/admin/products/pending', headers=headers).status_code == 403
    if role == 'BUYER':
        assert admitted.get('/api/v1/addresses', headers=headers).status_code == 200
        assert admitted.get('/api/v1/sellers/me', headers=headers).status_code == 403
    else:
        # Seller registration intentionally requires subsequent profile setup.
        assert admitted.post('/api/v1/sellers/me', headers=headers, json={
            'shop_name': 'Synthetic shop', 'phone': '9000000001',
            'latitude': '19', 'longitude': '72',
        }).status_code == 201
        assert admitted.get('/api/v1/sellers/me', headers=headers).status_code == 200
        assert admitted.post('/api/v1/discovery/products', headers=headers, json={}).status_code == 403
    assert admitted.post('/api/v1/auth/logout').status_code == 204
    assert admitted.cookies.get('wn_refresh') is None
    assert admitted.get('/api/v1/auth/me', headers=headers).status_code == 401
    assert admitted.post('/api/v1/auth/refresh').status_code == 401


def test_unapproved_registration_creates_no_account(admitted, db):
    response = register(admitted, email='unapproved@example.com')
    assert response.status_code == 403
    assert db.scalar(select(User)) is None


@pytest.mark.parametrize('role', ['BUYER', 'SELLER'])
def test_removed_admission_blocks_existing_login_access_and_refresh(admitted, role):
    assert register(admitted, role=role).status_code == 201
    signed_in = login(admitted)
    assert signed_in.status_code == 200
    headers = {'Authorization': 'Bearer ' + signed_in.json()['access_token']}
    admitted.app.state.settings.beta_allowed_emails = ['someone-else@example.com']
    assert login(admitted).status_code == 403
    assert admitted.get('/api/v1/auth/me', headers=headers).status_code == 403
    assert admitted.post('/api/v1/auth/refresh').status_code == 403


def test_admitted_duplicate_and_wrong_password(admitted):
    assert register(admitted).status_code == 201
    assert register(admitted, email='RAVI@example.com').status_code == 409
    assert login(admitted, password='wrong-password').status_code == 401


@pytest.mark.parametrize('kind', ['expired', 'wrong-signature', 'malformed'])
def test_invalid_access_tokens_are_rejected(admitted, kind):
    assert register(admitted).status_code == 201
    signed_in = login(admitted)
    claims = jwt.decode(signed_in.json()['access_token'], SECRET, algorithms=['HS256'])
    key = SECRET
    if kind == 'expired':
        now = int(datetime.now(timezone.utc).timestamp())
        claims.update(iat=now - 1000, exp=now - 1)
    elif kind == 'wrong-signature':
        key = 'different-synthetic-signing-key-' + 'x' * 40
    token = 'not.a.token' if kind == 'malformed' else jwt.encode(claims, key, algorithm='HS256')
    assert admitted.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_absolute_session_expiry_blocks_refresh(admitted, db):
    from app.models.auth_session import AuthSession
    assert register(admitted).status_code == 201
    signed_in = login(admitted)
    family = db.scalar(select(AuthSession))
    family.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.flush()
    assert admitted.post('/api/v1/auth/refresh').status_code == 401
    assert admitted.get('/api/v1/auth/me', headers={
        'Authorization': 'Bearer ' + signed_in.json()['access_token'],
    }).status_code == 401


@pytest.mark.parametrize('role', ['BUYER', 'SELLER'])
def test_open_beta_registration_login_and_refresh(auth_client, role):
    auth_client.app.state.settings = Settings(
        _env_file=None,
        environment='test',
        jwt_secret_key=SECRET,
        beta_registration_mode='open',
        beta_allowed_emails=['invited@example.com'],
    )

    email = 'new-resident@example.com'

    registered = register(auth_client, email=email, role=role)
    assert registered.status_code == 201, registered.text
    assert registered.json()['email'] == email
    assert registered.json()['role'] == role

    signed_in = login(auth_client, email=email)
    assert signed_in.status_code == 200, signed_in.text

    headers = {
        'Authorization': 'Bearer ' + signed_in.json()['access_token']
    }

    assert auth_client.get(
        '/api/v1/auth/me', headers=headers
    ).status_code == 200

    assert auth_client.post(
        '/api/v1/auth/refresh'
    ).status_code == 200

    assert auth_client.get(
        '/api/v1/admin/products/pending', headers=headers
    ).status_code == 403


def test_open_beta_rejects_admin_self_registration(auth_client):
    auth_client.app.state.settings = Settings(
        _env_file=None,
        environment='test',
        jwt_secret_key=SECRET,
        beta_registration_mode='open',
    )

    response = register(
        auth_client,
        email='new-admin@example.com',
        role='ADMIN',
    )

    assert response.status_code == 422, response.text
