from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models import Address, Order, OrderItem, Product, User
from test_authentication import auth_client
from test_authorization import bearer
from test_order_creation import order_payload


def headers(records, key):
    return {**bearer(records['buyer'].id), 'Idempotency-Key': str(key)}


def test_identical_retry_returns_same_order_and_deducts_once(auth_client, db, records, order_payload):
    key = uuid4()
    first = auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, key))
    retry = auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, key))
    assert first.status_code == retry.status_code == 201
    assert retry.json() == first.json()
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Order)) == 2  # one pre-existing fixture order
    assert db.scalar(select(func.count()).select_from(OrderItem)) == 2
    assert records['product'].stock_quantity == 3


def test_replay_returns_purchase_snapshot_even_when_product_no_longer_available(auth_client, db, records, order_payload):
    key = uuid4()
    order_payload['items'][0]['quantity'] = 5
    first = auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, key))
    assert first.status_code == 201
    records['product'].is_active = False
    records['product'].price = '999.00'
    records['seller'].dispatch_location_confirmed_at = None
    db.flush()
    retry = auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, key))
    assert retry.status_code == 201
    assert retry.json() == first.json()
    assert records['product'].stock_quantity == 0


@pytest.mark.parametrize('change', ['quantity', 'address', 'seller'])
def test_same_key_different_request_is_rejected(auth_client, db, records, order_payload, change):
    key = uuid4()
    assert auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, key)).status_code == 201
    changed = deepcopy(order_payload)
    if change == 'quantity':
        changed['items'][0]['quantity'] = 1
    else:
        changed[f'{change}_id'] = 999999
    response = auth_client.post('/api/v1/orders', json=changed, headers=headers(records, key))
    assert response.status_code == 409
    assert response.json()['code'] == 'IDEMPOTENCY_CONFLICT'
    db.expire_all()
    assert records['product'].stock_quantity == 3
    assert db.scalar(select(func.count()).select_from(Order)) == 2


def test_new_key_creates_new_order(auth_client, db, records, order_payload):
    first = auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, uuid4()))
    second = auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, uuid4()))
    assert first.status_code == second.status_code == 201
    assert first.json()['id'] != second.json()['id']
    db.expire_all()
    assert records['product'].stock_quantity == 1


def test_key_is_scoped_to_authenticated_buyer(auth_client, db, records, order_payload):
    key = uuid4()
    first = auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, key))
    other = User(name='Other buyer', email='idempotent-other@example.test', phone='idempotent-other', password_hash='hash', role='BUYER')
    address = Address(user=other, label='Home', address_line1='Other Lane', city='Mumbai', state='Maharashtra',
                      pincode='400001', latitude='19.070000', longitude='72.870000')
    db.add_all([other, address])
    db.flush()
    other_headers = {**bearer(other.id), 'Idempotency-Key': str(key)}
    assert auth_client.post('/api/v1/orders', json=order_payload, headers=other_headers).status_code == 403
    second = auth_client.post('/api/v1/orders', json={**order_payload, 'address_id': address.id}, headers=other_headers)
    assert second.status_code == 201
    assert second.json()['id'] != first.json()['id']
    assert second.json()['buyer_id'] == other.id
    assert auth_client.get(f"/api/v1/orders/{first.json()['id']}", headers=other_headers).status_code == 403


def test_item_order_is_not_a_material_request_change(auth_client, db, records, order_payload):
    product = Product(seller_id=records['seller'].id, name='Second item', description='Clay', price='25.00',
                      stock_quantity=5, category='Crafts', delivery_radius_km=2, status='APPROVED')
    db.add(product)
    db.flush()
    order_payload['items'].append(dict(product_id=product.id, quantity=1))
    key = uuid4()
    first = auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, key))
    changed = {**order_payload, 'items': list(reversed(order_payload['items']))}
    retry = auth_client.post('/api/v1/orders', json=changed, headers=headers(records, key))
    assert retry.status_code == 201
    assert retry.json() == first.json()
    db.expire_all()
    assert product.stock_quantity == 4


@pytest.mark.parametrize('key', [None, '', 'weak-key', '00000000-0000-1000-8000-000000000000', 'x' * 5000])
def test_missing_or_invalid_idempotency_key_rejected(auth_client, records, order_payload, key):
    supplied = bearer(records['buyer'].id)
    if key is not None:
        supplied['Idempotency-Key'] = key
    response = auth_client.post('/api/v1/orders', json=order_payload, headers=supplied)
    assert response.status_code == 422
    assert 'input' not in response.text


def test_business_failure_does_not_reserve_key_or_deduct_stock(auth_client, db, records, order_payload):
    key = uuid4()
    records['product'].stock_quantity = 1
    db.flush()
    assert auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, key)).status_code == 409
    records['product'].stock_quantity = 5
    db.flush()
    response = auth_client.post('/api/v1/orders', json=order_payload, headers=headers(records, key))
    assert response.status_code == 201
    assert records['product'].stock_quantity == 3


def test_outer_rollback_reverts_order_key_items_and_stock(db, records, order_payload):
    from app.services.inputs import OrderPlacement
    from app.services.orders import OrderService
    data = OrderPlacement(buyer_id=records['buyer'].id, idempotency_key=uuid4(), **order_payload)
    with pytest.raises(RuntimeError), db.begin_nested():
        OrderService(db).create(data)
        raise RuntimeError('Lost transaction before commit')
    db.expire_all()
    assert records['product'].stock_quantity == 5
    assert db.scalar(select(func.count()).select_from(Order)) == 1
    assert db.scalar(select(func.count()).select_from(OrderItem)) == 1
    OrderService(db).create(data)
    assert records['product'].stock_quantity == 3
    assert db.scalar(select(func.count()).select_from(Order)) == 2


def test_body_cannot_supply_the_idempotency_key(auth_client, records, order_payload):
    response = auth_client.post('/api/v1/orders', json={**order_payload, 'idempotency_key': str(uuid4())},
                               headers=headers(records, uuid4()))
    assert response.status_code == 422
