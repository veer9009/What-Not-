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
