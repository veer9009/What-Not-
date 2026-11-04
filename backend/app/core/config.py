from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WHAT_NOT_",
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )
    environment: Literal["development", "test", "production"] = "development"
    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=60)
    delivery_confirmation_grace_hours: int = Field(default=24, ge=1, le=168)
    property_reconfirmation_days: int = Field(default=30, ge=1, le=90)
    outbox_batch_size: int = Field(default=50, ge=1, le=100)
    outbox_lease_seconds: int = Field(default=120, ge=30, le=3600)
    outbox_max_attempts: int = Field(default=5, ge=1, le=10)
    outbox_backoff_seconds: int = Field(default=60, ge=1, le=3600)
    email_provider: Literal['disabled', 'smtp'] = 'disabled'
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = Field(default=None, repr=False)
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    smtp_timeout_seconds: int = Field(default=10, ge=1, le=30)
    email_from: str | None = None
    beta_allowed_emails: list[str] = Field(default_factory=list, repr=False)
    abuse_limits_enabled: bool = True
    discovery_hourly_limit: int = Field(default=60, ge=1, le=1000)
    address_daily_limit: int = Field(default=10, ge=1, le=100)
    checkout_daily_limit: int = Field(default=20, ge=1, le=100)
    auth_quarter_hour_limit: int = Field(default=20, ge=1, le=100)

    @field_validator('beta_allowed_emails')
    @classmethod
    def normalized_beta_accounts(cls, values):
        from pydantic import EmailStr, TypeAdapter
        return sorted({str(TypeAdapter(EmailStr).validate_python(value)).lower() for value in values})

    @model_validator(mode='after')
    def operational_configuration(self):
        if self.environment == 'production' and (not self.beta_allowed_emails or not self.abuse_limits_enabled):
            raise ValueError('Production beta requires an explicit account allowlist and abuse controls')
        if self.email_provider == 'smtp' and (not self.smtp_host or not self.email_from):
            raise ValueError('SMTP requires host and sender configuration')
        if self.email_from:
            from pydantic import EmailStr, TypeAdapter
            TypeAdapter(EmailStr).validate_python(self.email_from)
        if self.smtp_host and any(c in self.smtp_host for c in '\r\n'):
            raise ValueError('Invalid SMTP host')
        if self.outbox_lease_seconds <= self.smtp_timeout_seconds:
            raise ValueError('Outbox lease must exceed provider timeout')
        return self

    @field_validator("jwt_secret_key")
    @classmethod
    def strong_signing_key(cls, value):
        if value is not None:
            secret = value.get_secret_value()
            if len(secret.encode('utf-8')) < 32 or not secret.strip() or 'REPLACE_ME' in secret.upper():
                raise ValueError('JWT signing key requires at least 32 bytes from a secure random generator')
        return value

    @model_validator(mode='after')
    def production_signing_key(self):
        if self.environment == 'production' and self.jwt_secret_key is None:
            raise ValueError('WHAT_NOT_JWT_SECRET_KEY is required in production')
        return self
    database_url: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    @field_validator("database_url")
    @classmethod
    def postgres_psycopg_url(cls, value):
        if value is not None:
            from sqlalchemy.engine import make_url
            from sqlalchemy.exc import ArgumentError
            try:
                url = make_url(value.get_secret_value())
                if url.drivername != "postgresql+psycopg" or not url.database:
                    raise ValueError
            except (ArgumentError, ValueError, TypeError):
                raise ValueError("DATABASE_URL must be a postgresql+psycopg URL with a database") from None
        return value

    @field_validator("cors_origins")
    @classmethod
    def explicit_http_origins(cls, origins):
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths or credentials")
            # Accessing port validates malformed port strings too.
            parsed.port
        return origins
