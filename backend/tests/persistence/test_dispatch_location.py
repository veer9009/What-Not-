from decimal import Decimal

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text

from conftest import migration_config
from test_authentication import auth_client
from test_authorization import bearer


POINT = {'latitude': 19.076, 'longitude': 72.8777}
PATH = '/api/v1/sellers/me/dispatch-location'


def test_explicit_confirmation_and_legacy_edit_semantics(auth_client, records, db):
    headers = bearer(records['seller_user'].id)
    initial = auth_client.get('/api/v1/sellers/me', headers=headers).json()
    assert initial.get('dispatch_location_confirmed_at') is None
    result = auth_client.patch(PATH, json=POINT, headers=headers)
    assert result.status_code == 200
    confirmed = result.json()['dispatch_location_confirmed_at']
    assert confirmed
    db.expire_all()
    saved = auth_client.get('/api/v1/sellers/me', headers=headers).json()
    assert saved['dispatch_location_confirmed_at'] == confirmed
    assert Decimal(saved['latitude']) == Decimal('19.076')
    for patch in [{'shop_name': 'New name'}, {'latitude': '19.076000'}]:
        assert auth_client.patch('/api/v1/sellers/me', json=patch, headers=headers).json()['dispatch_location_confirmed_at'] == confirmed
    changed = auth_client.patch('/api/v1/sellers/me', json={'longitude': '73'}, headers=headers)
    assert changed.json()['dispatch_location_confirmed_at'] is None


@pytest.mark.parametrize('actor,status', [(None, 401), ('buyer', 403), ('seller_user', 200)])
def test_dispatch_roles(auth_client, records, actor, status):
    headers = bearer(records[actor].id) if actor else {}
    assert auth_client.patch(PATH, json=POINT, headers=headers).status_code == status


def test_inactive_and_admin_cannot_set_dispatch(auth_client, records, db):
    user = records['seller_user']
    headers = bearer(user.id)
    user.role = 'ADMIN'
    db.flush()
    assert auth_client.patch(PATH, json=POINT, headers=headers).status_code == 403
    user.role = 'SELLER'
    user.is_active = False
    db.flush()
    assert auth_client.patch(PATH, json=POINT, headers=headers).status_code == 401


@pytest.mark.parametrize('body', [{'latitude': 1}, {'longitude': 1},
    {**POINT, 'user_id': 1}, {**POINT, 'seller_id': 1},
    {**POINT, 'dispatch_location_confirmed_at': '2026-01-01'},
    {'latitude': 91, 'longitude': 0}, {'latitude': 0, 'longitude': -181},
    {'latitude': 'NaN', 'longitude': 0}, {'latitude': 0, 'longitude': 'Infinity'},
    {'latitude': True, 'longitude': 0}, {'latitude': .1234567, 'longitude': 0}])
def test_dispatch_invalid_payload_is_sanitized(auth_client, records, body):
    response = auth_client.patch(PATH, json=body, headers=bearer(records['seller_user'].id))
    assert response.status_code == 422
    assert all('input' not in issue and 'ctx' not in issue for issue in response.json()['detail'])
    assert Decimal(records['seller'].latitude) == Decimal('19.076000')


def test_profile_owner_derived_from_identity(auth_client, records, db):
    from app.models import User, SellerProfile
    other = User(name='Other', email='other-dispatch@example.com', phone='other-dispatch', password_hash='hash', role='SELLER')
    profile = SellerProfile(user=other, shop_name='Other', phone='other-dispatch', latitude=0, longitude=0)
    db.add(profile)
    db.flush()
    assert auth_client.patch(PATH, json={'latitude': 1, 'longitude': 2}, headers=bearer(other.id)).status_code == 200
    assert Decimal(records['seller'].latitude) == Decimal('19.076000')
    assert profile.latitude == 1


def test_confirmation_migration_preserves_legacy_rows(fresh_database_url):
    config = migration_config(fresh_database_url)
    command.upgrade(config, '0001')
    engine = create_engine(fresh_database_url)
    try:
        with engine.begin() as connection:
            uid = connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES ('Legacy','legacy@example.com','legacy','hash','SELLER') RETURNING id"))
            connection.execute(text("INSERT INTO seller_profiles(user_id,shop_name,phone,latitude,longitude) VALUES (:uid,'Legacy','legacy',19,72)"), {'uid': uid})
        command.upgrade(config, '0002')
        assert 'dispatch_location_confirmed_at' in {c['name'] for c in inspect(engine).get_columns('seller_profiles')}
        with engine.connect() as connection:
            row = connection.execute(text('SELECT latitude,longitude,dispatch_location_confirmed_at FROM seller_profiles')).one()
            assert tuple(row) == (Decimal('19'), Decimal('72'), None)
        command.downgrade(config, '0001')
        command.upgrade(config, '0002')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT count(*) FROM seller_profiles')) == 1
    finally:
        engine.dispose()
