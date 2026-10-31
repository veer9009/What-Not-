"""Authoritative placement checks, including calls that bypass frontend discovery."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import Order, OrderItem, Product
from app.services.inputs import OrderPlacement
from app.services.orders import OrderService
from test_authentication import auth_client
from test_authorization import bearer as authenticated_headers
from uuid import uuid4


def bearer(user_id, **claims):
    return {**authenticated_headers(user_id, **claims), 'Idempotency-Key': str(uuid4())}


@pytest.fixture
def geographic_order(db, records):
    records['seller'].latitude = Decimal('0')
    records['seller'].longitude = Decimal('0')
    records['seller'].dispatch_location_confirmed_at = datetime.now(timezone.utc)
    records['address'].latitude = Decimal('0')
    records['address'].longitude = Decimal('0.001')
    records['product'].status = 'APPROVED'
    db.flush()
    return dict(seller_id=records['seller'].id, address_id=records['address'].id,
                items=[dict(product_id=records['product'].id, quantity=2)])


def unchanged(db, records, products=()):
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Order)) == 1
    assert db.scalar(select(func.count()).select_from(OrderItem)) == 1
    assert records['product'].stock_quantity == 5
    assert all(product.stock_quantity == 5 for product in products)


@pytest.mark.parametrize('radius', [1, 2, 3])
@pytest.mark.parametrize('inside', [True, False])
def test_saved_address_radius_matches_discovery(auth_client, db, records, geographic_order, radius, inside):
    records['product'].delivery_radius_km = radius
    # These literal coordinates are the same boundary cases used by Phase 7 discovery.
    limits = {1: ('0.008993', '0.008994'), 2: ('0.017986', '0.017987'), 3: ('0.026979', '0.026980')}
    records['address'].longitude = Decimal(limits[radius][0 if inside else 1])
    db.flush()
    headers = bearer(records['buyer'].id)
    detail = auth_client.post(f"/api/v1/discovery/products/{records['product'].id}",
                             headers=headers, json={'address_id': records['address'].id})
    assert detail.status_code == (200 if inside else 404)
    response = auth_client.post('/api/v1/orders', headers=headers, json=geographic_order)
    assert response.status_code == (201 if inside else 409), response.text
    if inside:
        db.expire_all()
        assert records['product'].stock_quantity == 3
        assert db.scalar(select(func.count()).select_from(Order)) == 2
    else:
        assert response.json() == {'detail': 'This product is outside the selected delivery address.',
                                   'code': 'DELIVERY_INELIGIBLE'}
        unchanged(db, records)


@pytest.mark.parametrize('radius', [1, 2, 3])
@pytest.mark.parametrize('extra,eligible', [(0.0, True), (0.5e-9, True), (1e-9, True), (2e-9, False)])
def test_placement_matches_discovery_at_exact_tolerance(db, records, geographic_order, monkeypatch, radius, extra, eligible):
    from app.services import orders, discovery, errors
    from app.schemas.discovery import DiscoverySource
    # Six-decimal stored coordinates cannot express micrometre offsets. Inject only the
    # shared distance result, leaving the real boundary helper and DB transaction intact.
    monkeypatch.setattr(orders, 'distance_km', lambda *args: radius + extra, raising=False)
    monkeypatch.setattr(discovery, 'distance_km', lambda *args: radius + extra)
    records['product'].delivery_radius_km = radius
    db.flush()
    source = DiscoverySource(address_id=records['address'].id)
    if eligible:
        discovery.DiscoveryService(db).get(records['buyer'].id, records['product'].id, source)
        OrderService(db).create(OrderPlacement(buyer_id=records['buyer'].id, **geographic_order))
        assert records['product'].stock_quantity == 3
    else:
        with pytest.raises(errors.ProductNotFound):
            discovery.DiscoveryService(db).get(records['buyer'].id, records['product'].id, source)
        with pytest.raises(errors.ServiceError, match='outside the selected delivery address'):
            OrderService(db).create(OrderPlacement(buyer_id=records['buyer'].id, **geographic_order))
        unchanged(db, records)


def test_unconfirmed_dispatch_rejected_without_writes(auth_client, db, records, geographic_order):
    records['seller'].dispatch_location_confirmed_at = None
    db.flush()
    response = auth_client.post('/api/v1/orders', headers=bearer(records['buyer'].id), json=geographic_order)
    assert response.status_code == 409
    assert 'dispatch location' in response.json()['detail'].lower()
    unchanged(db, records)


def test_one_outside_item_rejects_whole_order(auth_client, db, records, geographic_order):
    records['product'].delivery_radius_km = 2
    records['address'].longitude = Decimal('0.013490')  # About 1.5 km: first item fits, second does not.
    other = Product(seller_id=records['seller'].id, name='Short radius bowl', description='Clay',
                    price='100.00', stock_quantity=5, category='Crafts', delivery_radius_km=1,
                    status='APPROVED')
    db.add(other)
    db.flush()
    geographic_order['items'].append(dict(product_id=other.id, quantity=2))
    response = auth_client.post('/api/v1/orders', headers=bearer(records['buyer'].id), json=geographic_order)
    assert response.status_code == 409
    assert response.json()['code'] == 'DELIVERY_INELIGIBLE'
    unchanged(db, records, [other])


def test_foreign_address_rejected_before_geographic_checks(auth_client, db, records, geographic_order):
    from app.models import User
    buyer = User(name='Other', email='other-geo@example.test', phone='geo-other', password_hash='test-hash', role='BUYER')
    db.add(buyer)
    db.flush()
    response = auth_client.post('/api/v1/orders', headers=bearer(buyer.id), json=geographic_order)
    assert response.status_code == 403
    unchanged(db, records)


@pytest.mark.parametrize('field,value', [('latitude', 0), ('longitude', 0), ('buyer_latitude', 0),
    ('buyer_longitude', 0), ('seller_latitude', 0), ('seller_longitude', 0), ('distance', 0),
    ('distance_km', 0), ('eligible', True), ('location', {'latitude': 0, 'longitude': 0})])
def test_checkout_rejects_spoofed_geography(auth_client, db, records, geographic_order, field, value):
    response = auth_client.post('/api/v1/orders', headers=bearer(records['buyer'].id),
                               json={**geographic_order, field: value})
    assert response.status_code == 422
    unchanged(db, records)


def test_rechecks_dispatch_and_radius_after_prior_discovery(auth_client, db, records, geographic_order):
    headers = bearer(records['buyer'].id)
    source = {'address_id': records['address'].id}
    assert auth_client.post(f"/api/v1/discovery/products/{records['product'].id}", headers=headers, json=source).status_code == 200
    records['seller'].longitude = Decimal('1')
    db.flush()
    response = auth_client.post('/api/v1/orders', headers=headers, json=geographic_order)
    assert response.status_code == 409
    unchanged(db, records)
