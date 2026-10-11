import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "what-not-api"}


def test_application_metadata_and_docs(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "What Not? API"
    assert schema["info"]["version"] == "0.1.0"
    assert all(path.startswith("/api/v1/") for path in schema["paths"])


def test_settings_read_environment_and_keep_default_origins(monkeypatch):
    monkeypatch.setenv("WHAT_NOT_ENVIRONMENT", "test")
    monkeypatch.setenv("WHAT_NOT_CORS_ORIGINS", '["http://localhost:3000"]')
    settings = Settings(_env_file=None)
    assert settings.environment == "test"
    assert settings.cors_origins == ["http://localhost:3000"]


def test_dotenv_configuration(tmp_path):
    env = tmp_path / ".env"
    env.write_text('WHAT_NOT_ENVIRONMENT=test\nWHAT_NOT_CORS_ORIGINS=["http://localhost:3000"]\n', encoding="utf-8")
    assert Settings(_env_file=env).cors_origins == ["http://localhost:3000"]


@pytest.mark.parametrize("origin", ["*", "file://local", "http://localhost:5173/path"])
def test_cors_requires_explicit_origins(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[origin])


def test_local_cors_preflight(client):
    response = client.options("/api/v1/products", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in response.headers
    rejected = client.options("/api/v1/products", headers={"Origin": "https://unlisted.example", "Access-Control-Request-Method": "POST"})
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
