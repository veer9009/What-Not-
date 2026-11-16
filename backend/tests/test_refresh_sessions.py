from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import create_access_token
from app.main import create_app


def settings():
    return Settings(_env_file=None, environment='test', jwt_secret_key='refresh-unit-' + 'x' * 40)


def test_session_bound_access_token_has_fifteen_minute_lifetime():
    config = settings()
    token = create_access_token(7, config, session_id='a' * 32)
    claims = jwt.decode(token, config.jwt_secret_key.get_secret_value(), algorithms=['HS256'])
    assert claims['sid'] == 'a' * 32
    assert claims['exp'] - claims['iat'] == 900


@pytest.mark.parametrize('path', ['login', 'refresh', 'logout'])
@pytest.mark.parametrize('headers', [{}, {'Origin': 'https://evil.example', 'X-WhatNot-CSRF': '1'},
    {'Origin': 'http://testserver'}, {'Origin': 'http://testserver', 'X-WhatNot-CSRF': '1', 'Sec-Fetch-Site': 'cross-site'}])
def test_cookie_auth_rejects_untrusted_requests_before_storage(path, headers):
    with TestClient(create_app(settings())) as client:
        result = client.post('/api/v1/auth/' + path, headers=headers,
            json={'email': 'buyer@example.com', 'password': 'test-password'})
    assert result.status_code == 403


def test_refresh_credentials_are_hashed_and_session_lifetimes_are_absolute():
    from app.services.refresh_sessions import token_digest, session_lifetime
    assert token_digest('secret') != 'secret'
    assert len(token_digest('secret')) == 64
    assert session_lifetime('BUYER').total_seconds() == 28800
    assert session_lifetime('SELLER').total_seconds() == 28800
    assert session_lifetime('ADMIN').total_seconds() == 900


def test_refresh_cookie_always_has_browser_security_attributes():
    from fastapi import Response
    from app.api.routes.auth import set_refresh_cookie
    response = Response()
    set_refresh_cookie(response, 'opaque', datetime.now(timezone.utc), 123)
    cookie = response.headers['set-cookie']
    assert 'wn_refresh=opaque' in cookie
    for value in ['HttpOnly', 'Secure', 'SameSite=strict', 'Path=/api/v1/auth', 'Max-Age=123']:
        assert value in cookie


def test_refresh_cookie_handles_database_timestamp_in_non_utc_timezone():
    from fastapi import Response
    from app.api.routes.auth import set_refresh_cookie
    response = Response()
    expiry = datetime(2030, 1, 2, 12, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    set_refresh_cookie(response, 'opaque', expiry, 3600)
    assert 'expires=Wed, 02 Jan 2030 07:00:00 GMT' in response.headers['set-cookie']


def test_refresh_cookie_rejects_ambiguous_naive_expiry():
    from fastapi import Response
    from app.api.routes.auth import set_refresh_cookie
    response = Response()
    with pytest.raises(ValueError, match='timezone-aware'):
        set_refresh_cookie(response, 'opaque', datetime(2030, 1, 2), 3600)
    assert 'set-cookie' not in response.headers
