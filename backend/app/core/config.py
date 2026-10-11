from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator
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
