from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from ipaddress import ip_address
import re

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
    prepaid_upi_enabled: bool = False
    approved_refund_policy_reference: str | None = None
    image_storage: Literal['local', 's3'] = 'local'
    image_local_directory: Path = Path(__file__).resolve().parents[2] / '.private-product-images'
    image_s3_bucket: str | None = None
    image_s3_region: str | None = None
    image_delivery_origin: str = 'http://127.0.0.1:8000'
    image_url_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    image_upload_hourly_limit: int = Field(default=30, ge=1, le=200)

    @model_validator(mode='after')
    def image_configuration(self):
        origin = urlsplit(self.image_delivery_origin)
        if (origin.scheme not in {'http', 'https'} or not origin.hostname or origin.path not in {'', '/'}
                or origin.username or origin.password or origin.query or origin.fragment):
            raise ValueError('Image delivery requires an explicit HTTP(S) origin')
        origin.port
        self.image_delivery_origin = self.image_delivery_origin.rstrip('/')
        if self.image_storage == 's3':
            if not self.image_s3_bucket or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', self.image_s3_bucket):
                raise ValueError('S3 image storage requires a bucket name')
            if self.environment == 'production' and origin.scheme != 'https':
                raise ValueError('Production image delivery requires HTTPS')
        return self
    jwt_secret_key: SecretStr | None = None
    password_recovery_key: SecretStr | None = None
    recovery_delivery_enabled: bool = False
    recovery_active_key: str | None = None
    recovery_encryption_keys: dict[str, SecretStr] = Field(default_factory=dict, repr=False)
    recovery_smtp_deadline_seconds: int = Field(default=10, ge=1, le=20)
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
    beta_registration_mode: Literal['controlled', 'open'] = 'controlled'
    beta_allowed_emails: list[str] = Field(default_factory=list, repr=False)
    abuse_limits_enabled: bool = True
    discovery_hourly_limit: int = Field(default=60, ge=1, le=1000)
    address_daily_limit: int = Field(default=10, ge=1, le=100)
    checkout_daily_limit: int = Field(default=20, ge=1, le=100)
    auth_quarter_hour_limit: int = Field(default=20, ge=1, le=100)
    trusted_hosts: list[str] = Field(default_factory=list)
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=20)
    database_pool_timeout_seconds: int = Field(default=10, ge=1, le=60)
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)

    @field_validator('beta_allowed_emails')
    @classmethod
    def normalized_beta_accounts(cls, values):
        from pydantic import EmailStr, TypeAdapter
        return sorted({str(TypeAdapter(EmailStr).validate_python(value)).lower() for value in values})

    @model_validator(mode='after')
    def operational_configuration(self):
        import base64
        decoded = []
        for key_id, value in self.recovery_encryption_keys.items():
            try:
                key = base64.b64decode(value.get_secret_value(), validate=True)
            except Exception:
                raise ValueError('Recovery encryption requires base64-encoded 32-byte keys') from None
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', key_id) or len(key) != 32:
                raise ValueError('Recovery encryption requires valid identifiers and 32-byte keys')
            if any(secret and (key == secret.get_secret_value().encode()
                               or value.get_secret_value() == secret.get_secret_value()) for secret in
                   (self.password_recovery_key, self.jwt_secret_key)):
                raise ValueError('Recovery encryption key must be independent')
            decoded.append(key)
        if len(decoded) != len(set(decoded)):
            raise ValueError('Recovery key versions must use distinct key material')
        if self.recovery_active_key is not None and self.recovery_active_key not in self.recovery_encryption_keys:
            raise ValueError('Recovery active encryption key is missing')
        if self.recovery_delivery_enabled and (not self.recovery_active_key or not self.password_recovery_key):
            raise ValueError('Recovery activation requires encryption and HMAC keys')
        if self.recovery_delivery_enabled and self.email_provider != 'smtp' and self.environment != 'test':
            raise ValueError('Recovery activation requires SMTP')
        if self.recovery_delivery_enabled and not self.smtp_starttls:
            raise ValueError('Recovery SMTP requires TLS')
        if self.recovery_smtp_deadline_seconds >= self.outbox_lease_seconds:
            raise ValueError('Recovery SMTP deadline must be shorter than the lease')
        if self.environment == 'production':
            if not self.abuse_limits_enabled:
                raise ValueError('Production beta requires abuse controls')
            if self.beta_registration_mode == 'controlled' and not self.beta_allowed_emails:
                raise ValueError('Controlled production beta requires an explicit account allowlist')
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

    @field_validator("jwt_secret_key", "password_recovery_key")
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

    @field_validator('trusted_hosts')
    @classmethod
    def explicit_host_names(cls, hosts):
        for host in hosts:
            if len(host) > 253 or any(not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?', label)
                                      for label in host.split('.')):
                raise ValueError('Trusted hosts must be explicit DNS names or IPv4 addresses without schemes, ports or wildcards')
        return sorted({host.lower() for host in hosts})

    @model_validator(mode='after')
    def production_transport(self):
        if self.environment != 'production':
            return self
        if self.database_url is None:
            raise ValueError('DATABASE_URL is required in production')
        if not self.trusted_hosts:
            raise ValueError('Production requires explicit WHAT_NOT_TRUSTED_HOSTS')
        if any(urlsplit(origin).scheme != 'https' for origin in self.cors_origins):
            raise ValueError('Production CORS origins must use HTTPS')
        if self.email_provider == 'smtp' and not self.smtp_starttls:
            raise ValueError('Production SMTP requires TLS')
        from sqlalchemy.engine import make_url
        url = make_url(self.database_url.get_secret_value())
        # Query overrides can silently replace the host/identity or weaken TLS.
        # Pool/connect resource bounds are supplied by the engine factory.
        if not url.host or not url.username or set(url.query) - {'sslmode', 'sslrootcert', 'application_name'}:
            raise ValueError('Production database requires an explicit host/user and only approved connection parameters')
        try:
            local = ip_address(url.host).is_loopback
        except ValueError:
            local = url.host.lower() == 'localhost'
        if not local and (url.query.get('sslmode') != 'verify-full' or
                          not isinstance(url.query.get('sslrootcert'), str) or
                          not url.query['sslrootcert'].strip()):
            raise ValueError('Remote production PostgreSQL requires sslmode=verify-full and sslrootcert')
        return self
