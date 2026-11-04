import pytest
from datetime import datetime, timezone
from sqlalchemy import func, select

from app.models import Order, Product, SellerProfile, User
from test_authentication import auth_client
from test_authorization import bearer as authenticated_headers
from uuid import uuid4


def bearer(user_id, **claims):
    return {**authenticated_headers(user_id, **claims), 'Idempotency-Key': str(uuid4())}


@pytest.fixture
def order_payload(db, records):
    records['product'].status = 'APPROVED'
    records['seller'].dispatch_location_confirmed_at = datetime.now(timezone.utc)
    db.flush()
    return dict(seller_id=records['seller'].id, address_id=records['address'].id,
                items=[dict(product_id=records['product'].id, quantity=2, expected_unit_price='250.00')])


def assert_no_creation(db, records):
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Order)) == 1
    assert records['product'].stock_quantity == 5


def test_buyer_creates_order_with_server_prices_and_reduces_stock(auth_client, db, records, order_payload):
    response = auth_client.post('/api/v1/orders', headers=bearer(records['buyer'].id), json=order_payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data['buyer_id'] == records['buyer'].id
    assert data['seller_id'] == records['seller'].id
    assert data['status'] == 'PLACED'
    assert data['subtotal'] == '500.00'
    assert data['delivery_fee'] == '0.00'
    assert data['total'] == '500.00'
    assert data['items'] == [dict(product_id=records['product'].id, seller_id=records['seller'].id,
                                  name='Handmade vase', unit_price='250.00', quantity=2)]
    db.expire_all()
    stored = db.get(Order, data['id'])
    assert stored.buyer_id == records['buyer'].id
    assert stored.address_id == records['address'].id
    assert records['product'].stock_quantity == 3
    assert auth_client.get(f"/api/v1/orders/{data['id']}", headers=bearer(records['buyer'].id)).json() == data


@pytest.mark.parametrize('field,value', [('buyer_id', 999999), ('status', 'DELIVERED'),
    ('subtotal', '0.00'), ('delivery_fee', '0.00'), ('total', '0.00'), ('stock_quantity', 999)])
def test_order_rejects_spoofed_server_fields(auth_client, db, records, order_payload, field, value):
    response = auth_client.post('/api/v1/orders', headers=bearer(records['buyer'].id),
                               json={**order_payload, field: value})
    assert response.status_code == 422
    assert_no_creation(db, records)


def test_address_must_belong_to_authenticated_buyer(auth_client, db, records, order_payload):
    other = User(name='Other buyer', email='other@example.test', phone='1000000003',
                 password_hash='test-only-hash', role='BUYER')
    db.add(other)
    db.flush()
    response = auth_client.post('/api/v1/orders', headers=bearer(other.id), json=order_payload)
    assert response.status_code == 403
    assert_no_creation(db, records)


def test_mixed_seller_products_rejected_atomically(auth_client, db, records, order_payload):
    owner = User(name='Other seller', email='other-seller@example.test', phone='1000000004',
                 password_hash='test-only-hash', role='SELLER')
    seller = SellerProfile(user=owner, shop_name='Other shop', phone='1000000004', latitude=0, longitude=0)
    product = Product(seller=seller, name='Other product', description='Other', price='10.00',
                      stock_quantity=4, category='Crafts', delivery_radius_km=2, status='APPROVED')
    db.add_all([owner, seller, product])
    db.flush()
    order_payload['items'].append(dict(product_id=product.id, quantity=1, expected_unit_price='10.00'))
    response = auth_client.post('/api/v1/orders', headers=bearer(records['buyer'].id), json=order_payload)
    assert response.status_code == 403
    assert_no_creation(db, records)
    assert product.stock_quantity == 4


def test_insufficient_stock_rejected_without_creating_order(auth_client, db, records, order_payload):
    order_payload['items'][0]['quantity'] = 6
    response = auth_client.post('/api/v1/orders', headers=bearer(records['buyer'].id), json=order_payload)
    assert response.status_code == 409
    assert_no_creation(db, records)


def test_duplicate_products_rejected_without_stock_change(auth_client, db, records, order_payload):
    order_payload['items'].append(dict(product_id=records['product'].id, quantity=1))
    response = auth_client.post('/api/v1/orders', headers=bearer(records['buyer'].id), json=order_payload)
    assert response.status_code == 422
    assert_no_creation(db, records)


@pytest.mark.parametrize('role', ['SELLER', 'ADMIN'])
def test_nonbuyer_cannot_create_even_with_forged_buyer_claim(auth_client, db, records, order_payload, role):
    records['seller_user'].role = role
    db.flush()
    response = auth_client.post('/api/v1/orders', headers=bearer(records['seller_user'].id, role='BUYER'),
                               json=order_payload)
    assert response.status_code == 403
    assert_no_creation(db, records)


def test_order_creation_requires_authentication_without_opening_storage(client):
    response = client.post('/api/v1/orders', json=dict(seller_id=1, address_id=1,
                           items=[dict(product_id=1, quantity=1)]))
    assert response.status_code == 401
    assert client.app.state.database_engine is None
