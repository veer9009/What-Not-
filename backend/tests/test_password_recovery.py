import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


@pytest.mark.parametrize('path,payload', [
    ('request', {'email': 'person@example.com'}),
    ('verify', {'challenge': 'a' * 43, 'otp': '123456'}),
    ('reset', {'reset_token': 'a' * 43, 'password': 'new password'}),
])
def test_recovery_rejects_missing_csrf_before_storage(path, payload):
    with TestClient(create_app(Settings(_env_file=None, environment='test'))) as client:
        response = client.post('/api/v1/auth/password-recovery/' + path, json=payload)
    assert response.status_code == 403
    assert response.headers['cache-control'] == 'no-store'


def test_recovery_rejects_weak_hmac_key():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, password_recovery_key='weak')


def test_recovery_reset_preserves_password_spaces():
    from app.schemas.auth_recovery import RecoveryReset
    assert RecoveryReset(reset_token='a' * 43, password='  new password  ').password.get_secret_value() == '  new password  '


@pytest.mark.parametrize('environment', ['development', 'test'])
@pytest.mark.parametrize('path,payload', [
    ('request', {'email': 'person@example.com'}),
    ('verify', {'challenge': 'a' * 43, 'otp': '123456'}),
    ('reset', {'reset_token': 'a' * 43, 'password': 'new password'}),
])
def test_live_recovery_is_disabled_before_storage_even_with_smtp(environment, path, payload):
    from app.services.mail import FakeMailProvider
    config = Settings(_env_file=None, environment=environment, password_recovery_key='x' * 48,
                      email_provider='smtp', smtp_host='smtp.invalid', email_from='test@example.com')
    app = create_app(config)
    if environment != 'test':
        app.state.recovery_mail_provider = FakeMailProvider()
    with TestClient(app, base_url='https://testserver') as client:
        response = client.post('/api/v1/auth/password-recovery/' + path,
                               headers={'Origin': 'https://testserver', 'X-WhatNot-CSRF': '1'}, json=payload)
    assert response.status_code == 503
    assert response.json() == {'detail': 'Password recovery is unavailable'}


def test_recovery_delivery_never_uses_live_smtp(monkeypatch):
    from app.services.auth_recovery import deliver_recovery
    from app.services.mail import SMTPMailProvider
    def forbidden(*args, **kwargs):
        pytest.fail('Recovery must not contact SMTP before durable delivery is implemented')
    monkeypatch.setattr(SMTPMailProvider, 'send', forbidden)
    config = Settings(_env_file=None, email_provider='smtp', smtp_host='smtp.invalid', email_from='test@example.com')
    deliver_recovery(config, ('person@example.com', 'a' * 43, '123456'))
