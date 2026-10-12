import secrets

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize('secret', ['short', 'REPLACE_ME', ' ' * 40])
def test_weak_or_placeholder_jwt_secrets_are_rejected(secret):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret_key=secret)


def test_production_requires_explicit_secret(monkeypatch):
    monkeypatch.delenv('WHAT_NOT_JWT_SECRET_KEY', raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment='production')


@pytest.mark.parametrize('values', [dict(jwt_algorithm='none'), dict(jwt_algorithm='HS384'),
    dict(access_token_expire_minutes=0), dict(access_token_expire_minutes=61)])
def test_security_configuration_bounds(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_configured_lifetime_and_token_contents():
    import jwt
    from app.core.security import create_access_token, decode_access_token
    secret = 'isolated-test-unit-key-' + 'x' * 40
    settings = Settings(_env_file=None, environment='test', jwt_secret_key=secret,
                        access_token_expire_minutes=2)
    token = create_access_token(7, settings)
    assert decode_access_token(token, settings) == 7
    claims = jwt.decode(token, secret, algorithms=['HS256'])
    assert set(claims) == {'sub', 'iat', 'exp'}
    assert claims['sub'] == '7' and claims['exp'] - claims['iat'] == 120
    assert secret not in repr(settings)


@pytest.mark.parametrize('changes', [{'sub': '0'}, {'sub': '01'}, {'sub': '9223372036854775808'},
    {'sub': 7}, {'sub': 'abc'}, {'exp': 1}, {'iat': 9999999999}, {'exp': None},
    {'iat': True}, {'exp': 9999999999.5}, {'iat': '1'}, {'exp': '9999999999'}])
def test_token_boundary_rejects_invalid_subject_and_time_claims(changes):
    import time
    import jwt
    from app.core.security import decode_access_token, InvalidCredentials
    secret = 'isolated-test-unit-key-' + 'x' * 40
    settings = Settings(_env_file=None, environment='test', jwt_secret_key=secret)
    payload = {'sub': '7', 'iat': int(time.time()), 'exp': int(time.time()) + 120, **changes}
    token = jwt.encode(payload, secret, algorithm='HS256')
    with pytest.raises(InvalidCredentials):
        decode_access_token(token, settings)


def test_password_helpers_preserve_exact_unicode_and_handle_invalid_hash():
    from app.core.security import hash_password, verify_password
    password = f' {chr(0x5BC6)}{chr(0x7801)} {secrets.token_urlsafe(24)} '
    encoded = hash_password(password)
    assert encoded.startswith('$argon2id$')
    assert verify_password(password, encoded)
    assert not verify_password(password.strip(), encoded)
    assert not verify_password(password, 'broken stored value')
