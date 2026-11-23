"""Security checks for open and controlled beta registration."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.abuse import require_beta_admission


def settings(**overrides):
    values = {
        "environment": "production",
        "jwt_secret_key": "synthetic-test-key-" + "x" * 40,
        "database_url": "postgresql+psycopg://test@127.0.0.1/test",
        "cors_origins": ["https://pilot.example.test"],
        "trusted_hosts": ["pilot.example.test"],
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_open_mode_accepts_unlisted_email():
    config = settings(beta_registration_mode="open")
    require_beta_admission(config, "resident@example.com")


def test_controlled_mode_blocks_unlisted_email():
    from fastapi import HTTPException

    config = settings(
        beta_registration_mode="controlled",
        beta_allowed_emails=["invited@example.com"],
    )
    with pytest.raises(HTTPException) as error:
        require_beta_admission(config, "resident@example.com")
    assert error.value.status_code == 403


def test_open_mode_requires_abuse_protection():
    with pytest.raises(ValidationError):
        settings(
            beta_registration_mode="open",
            abuse_limits_enabled=False,
        )


def test_controlled_mode_requires_allowlist():
    with pytest.raises(ValidationError):
        settings(beta_registration_mode="controlled")


def test_invalid_registration_mode_rejected():
    with pytest.raises(ValidationError):
        settings(beta_registration_mode="unrestricted")
