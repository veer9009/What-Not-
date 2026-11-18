"""Synthetic configuration only; never load the repository's private .env."""
import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    import os
    for key in tuple(os.environ):
        if key.upper().startswith('WHAT_NOT_') or key.upper() == 'DATABASE_URL':
            monkeypatch.delenv(key)


def production(**changes):
    return Settings(_env_file=None, **(dict(
        environment='production', jwt_secret_key='synthetic-config-only-' + 'x' * 40,
        database_url='postgresql+psycopg://synthetic@127.0.0.1/unit_only',
        cors_origins=['https://pilot.example.test'], trusted_hosts=['pilot.example.test'],
    ) | changes))


def test_environment_json_normalizes_and_deduplicates_admitted_emails(monkeypatch):
    monkeypatch.setenv('WHAT_NOT_BETA_ALLOWED_EMAILS', '["Buyer@Example.com","SELLER@example.com","buyer@example.com"]')
    settings = production()
    assert settings.beta_allowed_emails == ['buyer@example.com', 'seller@example.com']
    assert settings.abuse_limits_enabled


def test_dotenv_json_and_process_environment_precedence(tmp_path, monkeypatch):
    dotenv = tmp_path / 'synthetic.env'
    dotenv.write_text('WHAT_NOT_BETA_ALLOWED_EMAILS=\'["Buyer@Example.com","Seller@example.com"]\'\n', encoding='utf-8')
    assert Settings(_env_file=dotenv).beta_allowed_emails == ['buyer@example.com', 'seller@example.com']
    monkeypatch.setenv('WHAT_NOT_BETA_ALLOWED_EMAILS', '["Operator@example.com"]')
    assert Settings(_env_file=dotenv).beta_allowed_emails == ['operator@example.com']


@pytest.mark.parametrize('value', [None, '[]'])
def test_production_rejects_missing_or_empty_allowlist(monkeypatch, value):
    if value is not None:
        monkeypatch.setenv('WHAT_NOT_BETA_ALLOWED_EMAILS', value)
    with pytest.raises(ValidationError, match='explicit account allowlist and abuse controls'):
        production()


@pytest.mark.parametrize('value', ['buyer@example.com,seller@example.com', "['buyer@example.com']", '', '"buyer@example.com"', '["invalid"]'])
def test_invalid_allowlist_format_fails_closed(monkeypatch, value):
    monkeypatch.setenv('WHAT_NOT_BETA_ALLOWED_EMAILS', value)
    with pytest.raises((SettingsError, ValidationError)):
        production()


def test_production_rejects_disabled_abuse_with_valid_allowlist():
    with pytest.raises(ValidationError, match='explicit account allowlist and abuse controls'):
        production(beta_allowed_emails=['buyer@example.com'], abuse_limits_enabled=False)
