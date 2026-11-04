"""Delivery completion belongs to the owning buyer, including at the HTTP boundary."""
import pytest

from app.models import User
from app.services.errors import InvalidOrderTransition, OwnershipError
from test_authentication import auth_client
from test_authorization import bearer
from test_services_marketplace import market, place
from test_service_concurrency import concurrency_engine, seed, race_while_locked


def test_seller_handover_then_buyer_confirmation_preserves_inventory(market):
    m = market
    order = place(m)
    for status in ['ACCEPTED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED']:
        assert m['orders'].transition(m['owner'].id, order.id, status).status == status
    with pytest.raises(OwnershipError):
        m['orders'].transition(m['owner'].id, order.id, 'COMPLETED')
    assert m['orders'].transition(m['buyer'].id, order.id, 'COMPLETED').status == 'COMPLETED'
    with pytest.raises(InvalidOrderTransition):
        m['orders'].transition(m['buyer'].id, order.id, 'COMPLETED')
    assert m['products'].get(m['product'].id).stock_quantity == 3


@pytest.mark.parametrize('start', ['PLACED', 'ACCEPTED', 'PREPARING', 'OUT_FOR_DELIVERY', 'COMPLETED', 'CANCELLED', 'REJECTED'])
def test_buyer_confirmation_rejects_every_other_status(db, market, start):
    m = market
    order = place(m)
    order.status = start
    db.flush()
    with pytest.raises(InvalidOrderTransition):
        m['orders'].transition(m['buyer'].id, order.id, 'COMPLETED')
    assert m['orders'].get(m['buyer'].id, order.id).status == start
    assert m['products'].get(m['product'].id).stock_quantity == 3


@pytest.mark.parametrize('start', ['OUT_FOR_DELIVERY', 'DELIVERED'])
def test_seller_cannot_finalize_delivery(db, market, start):
    m = market
    order = place(m)
    order.status = start
    db.flush()
    with pytest.raises(OwnershipError):
        m['orders'].transition(m['owner'].id, order.id, 'COMPLETED')
    assert m['orders'].get(m['buyer'].id, order.id).status == start


@pytest.mark.parametrize('role', ['BUYER', 'SELLER', 'ADMIN'])
def test_unrelated_actor_cannot_confirm_receipt(db, market, role):
    m = market
    order = place(m)
    order.status = 'DELIVERED'
    actor = User(name='Other', email='other-receipt@example.test', phone='other-receipt',
                 password_hash='test-only-hash', role=role)
    db.add(actor)
    db.flush()
    with pytest.raises(OwnershipError):
        m['orders'].transition(actor.id, order.id, 'COMPLETED')
    assert m['orders'].get(m['buyer'].id, order.id).status == 'DELIVERED'


@pytest.mark.parametrize('actor,status,want', [
    ('seller_user', 'DELIVERED', 200),
    ('seller_user', 'COMPLETED', 403),
    ('buyer', 'DELIVERED', 403),
    ('buyer', 'COMPLETED', 409),
])
def test_status_api_handover_contract(auth_client, db, records, actor, status, want):
    order = records['order']
    order.status = 'OUT_FOR_DELIVERY'
    db.flush()
    response = auth_client.patch(f'/api/v1/orders/{order.id}/status',
                                 headers=bearer(records[actor].id), json={'status': status})
    assert response.status_code == want, response.text
    assert auth_client.get(f'/api/v1/orders/{order.id}', headers=bearer(records['buyer'].id)).json()['status'] == (
        status if want == 200 else 'OUT_FOR_DELIVERY')


def test_status_api_buyer_completion_and_duplicate(auth_client, db, records):
    order = records['order']
    order.status = 'DELIVERED'
    db.flush()
    path = f'/api/v1/orders/{order.id}/status'
    headers = bearer(records['buyer'].id)
    response = auth_client.patch(path, headers=headers, json={'status': 'COMPLETED'})
    assert response.status_code == 200 and response.json()['status'] == 'COMPLETED'
    assert auth_client.patch(path, headers=headers, json={'status': 'COMPLETED'}).status_code == 409
    assert records['product'].stock_quantity == 5


@pytest.mark.parametrize('role', ['BUYER', 'SELLER', 'ADMIN'])
def test_status_api_other_users_cannot_confirm(auth_client, db, records, role):
    records['order'].status = 'DELIVERED'
    actor = User(name='Other', email='other-http@example.test', phone='other-http', password_hash='test-only-hash', role=role)
    db.add(actor)
    db.flush()
    path = f"/api/v1/orders/{records['order'].id}/status"
    assert auth_client.patch(path, headers=bearer(actor.id), json={'status': 'COMPLETED'}).status_code == 403
    assert records['order'].status == 'DELIVERED'


def test_legacy_delivered_order_remains_readable(auth_client, db, records):
    records['order'].status = 'COMPLETED'
    db.flush()
    for actor in ['buyer', 'seller_user']:
        headers = bearer(records[actor].id)
        assert auth_client.get(f"/api/v1/orders/{records['order'].id}", headers=headers).json()['status'] == 'COMPLETED'
        assert auth_client.get('/api/v1/orders', headers=headers).json()[0]['status'] == 'COMPLETED'


def test_duplicate_handover_is_conflict_and_stock_unchanged(db, market):
    m = market
    order = place(m)
    order.status = 'OUT_FOR_DELIVERY'
    db.flush()
    m['orders'].transition(m['owner'].id, order.id, 'DELIVERED')
    with pytest.raises(InvalidOrderTransition):
        m['orders'].transition(m['owner'].id, order.id, 'DELIVERED')
    assert m['products'].get(m['product'].id).stock_quantity == 3


@pytest.mark.parametrize('status', ['CANCELLED', 'REJECTED'])
def test_handover_cannot_be_cancelled_or_rejected(db, market, status):
    m = market
    order = place(m)
    order.status = 'DELIVERED'
    db.flush()
    with pytest.raises(InvalidOrderTransition):
        m['orders'].transition(m['owner'].id, order.id, status)
    assert m['products'].get(m['product'].id).stock_quantity == 3


@pytest.mark.parametrize('actor,start,target', [
    ('owner', 'OUT_FOR_DELIVERY', 'DELIVERED'),
    ('buyer', 'DELIVERED', 'COMPLETED'),
])
def test_concurrent_delivery_transitions_apply_once(concurrency_engine, actor, start, target):
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.models import Order, Product
    from app.services.inputs import OrderPlacement
    from app.services.orders import OrderService
    engine = concurrency_engine
    r = seed(engine)
    with Session(engine) as session, session.begin():
        order = OrderService(session).create(OrderPlacement(buyer_id=r['buyer'], seller_id=r['seller'],
            address_id=r['address'], items=[dict(product_id=r['product'], quantity=1)]))
        order.status = start
        order_id = order.id

    def transition(session):
        try:
            OrderService(session).transition(r[actor], order_id, target)
            return 'updated'
        except InvalidOrderTransition:
            return 'conflict'

    results = race_while_locked(engine, select(Order).where(Order.id == order_id).with_for_update(), [transition, transition])
    assert sorted(results) == ['conflict', 'updated']
    with Session(engine) as session:
        assert session.get(Order, order_id).status == target
        assert session.get(Product, r['product']).stock_quantity == 0


def test_unauthenticated_confirmation_rejected(auth_client, records):
    response = auth_client.patch(f"/api/v1/orders/{records['order'].id}/status", json={'status': 'COMPLETED'})
    assert response.status_code == 401
