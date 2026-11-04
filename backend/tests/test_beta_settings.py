import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_beta_settings_have_bounded_worker_defaults():
    settings = Settings(_env_file=None, environment='test')
    assert settings.delivery_confirmation_grace_hours == 24
    assert settings.property_reconfirmation_days == 30
    assert settings.outbox_max_attempts == 5
    assert settings.smtp_timeout_seconds == 10
    assert settings.email_provider == 'disabled'


@pytest.mark.parametrize('values', [
    {'delivery_confirmation_grace_hours': 0}, {'outbox_max_attempts': 0},
    {'smtp_timeout_seconds': 0}, {'discovery_hourly_limit': 0},
    {'email_provider': 'smtp', 'smtp_host': None},
])
def test_beta_settings_fail_closed_on_invalid_operational_values(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment='test', **values)


def test_production_requires_beta_admission_and_abuse_controls():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment='production', jwt_secret_key='x' * 48)
    settings = Settings(_env_file=None, environment='production', jwt_secret_key='x' * 48,
                        beta_allowed_emails=['Tester@Example.com'])
    assert settings.beta_allowed_emails == ['tester@example.com']
    assert settings.abuse_limits_enabled


def test_smtp_configuration_does_not_expose_password():
    settings = Settings(_env_file=None, environment='test', email_provider='smtp',
        smtp_host='smtp.example.test', email_from='orders@example.com',
        smtp_password='private-mail-password')
    assert 'private-mail-password' not in repr(settings)
