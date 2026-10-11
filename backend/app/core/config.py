from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WHAT_NOT_",
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    environment: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

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
