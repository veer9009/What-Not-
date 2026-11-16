"""Reproduce the local 0008 failure only in a disposable test database."""
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import Settings
from app.api.dependencies import get_current_user
from app.main import create_app
from app.models import User
from conftest import migration_config


def test_0009_restores_existing_seller_profile_without_backfilling_consent(fresh_database_url):
    config = migration_config(fresh_database_url)
    command.upgrade(config, '0008')
    engine = create_engine(fresh_database_url, hide_parameters=True)
    settings = Settings(_env_file=None, environment='test',
                        database_url=fresh_database_url.render_as_string(hide_password=False),
                        jwt_secret_key='isolated-seller-schema-test-' + 'x' * 40)
    try:
        with engine.begin() as connection:
            uid = connection.scalar(text("""INSERT INTO users(name,email,phone,password_hash,role)
                VALUES ('Legacy','legacy-schema@example.test','legacy-schema','hash','SELLER')
                RETURNING id"""))
            connection.execute(text("""INSERT INTO seller_profiles
                (user_id,shop_name,phone,latitude,longitude)
                VALUES (:uid,'Legacy shop','legacy-schema',19,72)"""), {'uid': uid})
        app = create_app(settings)
        # Authentication is covered separately: these historical revisions
        # precede auth_sessions and this test isolates seller-profile storage.
        app.dependency_overrides[get_current_user] = lambda: User(id=uid, role='SELLER', is_active=True)
        with TestClient(app) as client:
            failed = client.get('/api/v1/sellers/me')
            assert failed.status_code == 503
            assert failed.json() == {'detail': 'Storage operation is unavailable'}
            command.upgrade(config, '0009')
            response = client.get('/api/v1/sellers/me')
            assert response.status_code == 200
            profile = response.json()
            assert profile['shop_name'] == 'Legacy shop'
            assert profile['public_discovery_confirmed_at'] is None
            assert client.patch('/api/v1/sellers/me',
                                json={'shop_name': 'Updated shop'}).status_code == 200
            assert client.get('/api/v1/sellers/me').json()['shop_name'] == 'Updated shop'
        with engine.connect() as connection:
            assert connection.execute(text("""SELECT public_discovery_latitude,
                public_discovery_longitude,public_discovery_confirmed_at,
                public_discovery_consent_version FROM seller_profiles""")).one() == (None, None, None, None)
    finally:
        engine.dispose()
