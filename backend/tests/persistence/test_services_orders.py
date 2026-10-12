from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import Order, OrderItem, Product, ProductImage
from test_services_marketplace import HASH, market, place


def second_product(m, *, price='10.00', stock=5):
    from app.schemas.product import ProductCreate
    p = m['products'].create(m['owner'].id, m['seller'].id, ProductCreate(name='Bowl',
        description='Clay', price=price, stock_quantity=stock, category='Crafts', delivery_radius_km=1))
    m['moderation'].approve(m['admin'].id, p.id)
    return p


def placement(m, products):
    from app.services.inputs import OrderPlacement
    return OrderPlacement(buyer_id=m['buyer'].id, seller_id=m['seller'].id,
        address_id=m['address'].id, items=[dict(product_id=p.id, quantity=q) for p, q in products])


def test_multi_item_order_with_configurable_fee(db, market):
    from app.services.orders import DeliveryFeePolicy, OrderService
    m = market
    p2 = second_product(m)
    m['moderation'].approve(m['admin'].id, m['product'].id)
    order = OrderService(db, DeliveryFeePolicy('7.50')).create(placement(m, [(m['product'], 2), (p2, 3)]))
    assert order.subtotal == Decimal('81.00')
    assert order.delivery_fee == Decimal('7.50') and order.total_amount == Decimal('88.50')
    assert len(order.items) == 2
    assert m['product'].stock_quantity == 3 and p2.stock_quantity == 2


def test_mixed_seller_order_rejected_before_any_inventory_change(db, market):
    from app.services.inputs import UserCreate, SellerCreate
    from app.schemas.product import ProductCreate
    from app.services.errors import OwnershipError
    m = market
    owner = m['users'].create(UserCreate(name='Other', email='other@example.com', phone='400', password_hash=HASH, role='SELLER'))
    seller = m['sellers'].create(owner.id, SellerCreate(shop_name='Other', phone='400', latitude=0, longitude=0))
    p2 = m['products'].create(owner.id, seller.id, ProductCreate(name='Other', description='Other', price='10.00', stock_quantity=3, category='Crafts', delivery_radius_km=1))
    m['moderation'].approve(m['admin'].id, p2.id)
    m['moderation'].approve(m['admin'].id, m['product'].id)
    with pytest.raises(OwnershipError):
        m['orders'].create(placement(m, [(m['product'], 1), (p2, 1)]))
    assert db.scalar(select(func.count()).select_from(Order)) == 0
    assert m['product'].stock_quantity == 5 and p2.stock_quantity == 3


def test_late_item_failure_rolls_back_order_items_and_decrements(db, market, monkeypatch):
    # Trigger a real CHECK constraint after all validation and stock mutation.
    # Fault injection replaces only item construction, retaining PostgreSQL flush.
    from app.services import orders
    from app.services.errors import PersistenceConflict
    m = market
    p2 = second_product(m)
    m['moderation'].approve(m['admin'].id, m['product'].id)
    real_item = orders.OrderItem
    calls = 0

    def broken_item(**values):
        nonlocal calls
        calls += 1
        if calls == 2:
            values['quantity'] = 0
        return real_item(**values)

    monkeypatch.setattr(orders, 'OrderItem', broken_item)
    with pytest.raises(PersistenceConflict) as caught:
        m['orders'].create(placement(m, [(m['product'], 2), (p2, 2)]))
    assert 'INSERT' not in str(caught.value) and 'CHECK' not in str(caught.value)
    assert db.scalar(select(func.count()).select_from(Order)) == 0
    assert db.scalar(select(func.count()).select_from(OrderItem)) == 0
    assert m['products'].get(m['product'].id).stock_quantity == 5
    assert m['products'].get(p2.id).stock_quantity == 5


@pytest.mark.parametrize('fee', ['0.00', '0.01'])
def test_order_amount_overflow_before_stock_changes(db, market, fee):
    from app.services.orders import DeliveryFeePolicy, OrderService
    from app.services.errors import AmountOverflow
    from app.schemas.product import ProductUpdate
    m = market
    m['products'].update(m['owner'].id, m['product'].id, ProductUpdate(price='9999999999.99'))
    m['moderation'].approve(m['admin'].id, m['product'].id)
    quantity = 2 if fee == '0.00' else 1
    with pytest.raises(AmountOverflow):
        OrderService(db, DeliveryFeePolicy(fee)).create(placement(m, [(m['product'], quantity)]))
    assert db.scalar(select(func.count()).select_from(Order)) == 0
    assert m['products'].get(m['product'].id).stock_quantity == 5


def test_restock_overflow_rolls_back_status_and_all_items(db, market):
    from app.services.errors import AmountOverflow
    m = market
    p2 = second_product(m)
    m['moderation'].approve(m['admin'].id, m['product'].id)
    order = m['orders'].create(placement(m, [(m['product'], 2), (p2, 2)]))
    p2.stock_quantity = 2147483647
    db.flush()
    with pytest.raises(AmountOverflow):
        m['orders'].transition(m['buyer'].id, order.id, 'CANCELLED')
    assert m['orders'].get(m['buyer'].id, order.id).status == 'PLACED'
    assert m['products'].get(m['product'].id).stock_quantity == 3
    assert m['products'].get(p2.id).stock_quantity == 2147483647


@pytest.mark.parametrize('start,end', [
    ('PLACED', 'PREPARING'), ('PLACED', 'DELIVERED'), ('ACCEPTED', 'REJECTED'),
    ('PREPARING', 'CANCELLED'), ('PREPARING', 'REJECTED'), ('OUT_FOR_DELIVERY', 'CANCELLED'),
    ('DELIVERED', 'ACCEPTED'), ('CANCELLED', 'ACCEPTED'), ('REJECTED', 'PLACED')])
def test_invalid_order_transitions_preserve_stock_and_status(db, market, start, end):
    from app.services.errors import InvalidOrderTransition
    m = market
    order = place(m)
    order.status = start
    db.flush()
    with pytest.raises(InvalidOrderTransition):
        m['orders'].transition(m['owner'].id, order.id, end)
    assert m['orders'].get(m['buyer'].id, order.id).status == start
    assert m['products'].get(m['product'].id).stock_quantity == 3


def test_product_primary_image_edit_preserves_other_images(db, market):
    from app.schemas.product import ProductUpdate
    m = market
    m['product'].images.append(ProductImage(image_url='https://example.com/secondary.jpg', is_primary=False, sort_order=1))
    db.flush()
    m['products'].update(m['owner'].id, m['product'].id, ProductUpdate(image_url=None))
    assert len(m['product'].images) == 1
    assert m['product'].images[0].image_url == 'https://example.com/secondary.jpg'


def test_service_requires_outer_transaction(migrated_engine):
    from sqlalchemy.orm import Session
    from app.services.users import UserService
    from app.services.inputs import UserCreate
    with Session(migrated_engine) as session:
        with pytest.raises(RuntimeError, match='outer transaction'):
            UserService(session).create(UserCreate(name='No transaction', email='no@example.com', phone='none', password_hash=HASH, role='BUYER'))


def test_missing_records_are_domain_errors(market):
    from app.services.errors import UserNotFound, SellerNotFound, ProductNotFound, AddressNotFound, OrderNotFound
    m = market
    for call, error in [
        (lambda: m['users'].get(999999), UserNotFound),
        (lambda: m['sellers'].get(999999), SellerNotFound),
        (lambda: m['products'].get(999999), ProductNotFound),
        (lambda: m['addresses'].get(m['buyer'].id, 999999), AddressNotFound),
        (lambda: m['orders'].get(m['buyer'].id, 999999), OrderNotFound)]:
        with pytest.raises(error):
            call()


@pytest.mark.parametrize('kind', ['product', 'user', 'empty_order', 'nested_quantity'])
def test_mutated_models_rejected_at_actual_service_boundary(db, market, kind):
    from pydantic import SecretStr, ValidationError
    from app.schemas.product import ProductCreate
    from app.services.inputs import UserCreate
    m = market
    if kind == 'product':
        data = ProductCreate(name='Free', description='Invalid', price='1.00', stock_quantity=1, category='Crafts', delivery_radius_km=1)
        data.price = Decimal('0')
        action = lambda: m['products'].create(m['owner'].id, m['seller'].id, data)
    elif kind == 'user':
        data = UserCreate(name='Plaintext', email='bad@example.com', phone='500', password_hash=HASH, role='BUYER')
        data.password_hash = SecretStr('plaintext')
        action = lambda: m['users'].create(data)
    else:
        data = placement(m, [(m['product'], 1)])
        if kind == 'empty_order':
            data.items.clear()
        else:
            data.items[0].quantity = True
        action = lambda: m['orders'].create(data)
    with pytest.raises(ValidationError):
        action()
    assert db.scalar(select(func.count()).select_from(Order)) == 0
    assert m['products'].get(m['product'].id).stock_quantity == 5


def test_implicit_read_transaction_cannot_write(migrated_engine):
    from sqlalchemy.orm import Session
    from sqlalchemy import text
    from app.services.users import UserService
    from app.services.inputs import UserCreate
    with Session(migrated_engine) as session:
        session.execute(text('SELECT 1'))
        with pytest.raises(RuntimeError, match='explicit outer transaction'):
            UserService(session).create(UserCreate(name='Implicit', email='implicit@example.com', phone='implicit', password_hash=HASH, role='BUYER'))
