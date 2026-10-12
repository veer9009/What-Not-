from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_and_placeholders_do_not_build_database_engine(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    app = create_app(Settings(_env_file=None))
    with TestClient(app) as client:
        assert client.get('/api/v1/health').status_code == 200
        assert client.get('/api/v1/products').status_code == 501
        assert app.state.database_engine is None


def test_health_does_not_connect_to_configured_unreachable_database():
    app = create_app(Settings(_env_file=None, database_url='postgresql+psycopg://test:test@127.0.0.1:1/whatnot_test_unreachable'))
    with TestClient(app) as client:
        assert client.get('/api/v1/health').status_code == 200
        assert app.state.database_engine is None
