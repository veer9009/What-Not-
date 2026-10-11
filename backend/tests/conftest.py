import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app(Settings(_env_file=None, environment="test"))) as client:
        yield client
