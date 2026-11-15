"""Production boundary tests: synthetic settings and no database connections."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def production(**overrides):
    return Settings(_env_file=None, **(dict(
        environment='production', jwt_secret_key='synthetic-production-unit-key-' + 'x' * 40,
        beta_allowed_emails=['pilot@example.com'],
        database_url='postgresql+psycopg://runtime:synthetic@127.0.0.1/pilot_unit',
        cors_origins=['https://pilot.example.test'], trusted_hosts=['pilot.example.test'],
    ) | overrides))


@pytest.mark.parametrize('overrides', [
    {'database_url': None}, {'cors_origins': ['http://pilot.example.test']},
    {'trusted_hosts': []}, {'trusted_hosts': ['*']}, {'trusted_hosts': ['*.example.test']},
    {'trusted_hosts': ['https://pilot.example.test']},
    {'email_provider': 'smtp', 'smtp_host': 'smtp.example.test',
     'email_from': 'pilot@example.com', 'smtp_starttls': False},
    {'database_url': 'postgresql+psycopg://runtime:synthetic@db.example.test/pilot_unit'},
    {'database_url': 'postgresql+psycopg://runtime:synthetic@db.example.test/pilot_unit?sslmode=require'},
    {'database_url': 'postgresql+psycopg://runtime:synthetic@db.example.test/pilot_unit?sslmode=verify-full'},
    {'database_url': 'postgresql+psycopg://runtime:synthetic@db.example.test/pilot_unit?sslmode=verify-full&sslrootcert=/etc/ssl/test-ca.pem&host=127.0.0.1'},
    {'database_url': 'postgresql+psycopg://runtime:synthetic@127.0.0.1/pilot_unit?host=db.example.test'},
    {'database_url': 'postgresql+psycopg://runtime:synthetic@db.example.test/pilot_unit?sslmode=verify-full&sslrootcert=/etc/ssl/test-ca.pem&options=-c%20log_statement=all'},
])
def test_production_rejects_incomplete_or_insecure_configuration(overrides):
    with pytest.raises(ValidationError):
        production(**overrides)


def test_production_accepts_loopback_or_explicit_verified_remote_database():
    assert production().environment == 'production'
    assert production(database_url='postgresql+psycopg://runtime:synthetic@db.example.test/pilot_unit?sslmode=verify-full&sslrootcert=/etc/ssl/test-ca.pem').database_url


def test_production_host_and_metadata_boundaries_without_connecting_database():
    app = create_app(production())
    with TestClient(app, base_url='https://pilot.example.test') as client:
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert response.headers['referrer-policy'] == 'no-referrer'
        assert response.headers['x-frame-options'] == 'DENY'
        assert response.headers['cache-control'] == 'no-store'
        for path in ['/docs', '/redoc', '/openapi.json']:
            assert client.get(path).status_code == 404
        assert client.get('/api/v1/health', headers={'Host': 'attacker.example.test'}).status_code == 400
        assert app.state.database_engine is None


def test_development_keeps_local_docs_and_optional_database():
    app = create_app(Settings(_env_file=None, environment='development', database_url=None))
    with TestClient(app) as client:
        assert client.get('/docs').status_code == 200
        assert client.get('/api/v1/health').status_code == 200


@pytest.mark.parametrize('values', [{'database_pool_size': 0}, {'database_max_overflow': -1},
    {'database_pool_timeout_seconds': 0}, {'database_connect_timeout_seconds': 0}])
def test_database_resource_limits_are_bounded(values):
    with pytest.raises(ValidationError):
        production(**values)
