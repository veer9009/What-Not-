from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.models import Address, Order, OrderItem, Product, User

# Precomputed bcrypt-format fixture; no password hashing or login is exercised.
HASH = '$2b$12$' + 'a' * 53


@pytest.fixture
def market(db):
    from app.services.users import UserService
    from app.services.sellers import SellerService
    from app.services.products import ProductService
    from app.services.addresses import AddressService
    from app.services.moderation import ModerationService
    from app.services.orders import OrderService
    from app.services.inputs import UserCreate, SellerCreate, AddressCreate
    from app.schemas.product import ProductCreate
    users = UserService(db)
    buyer = users.create(UserCreate(name='Buyer', email='b@example.com', phone='100', password_hash=HASH, role='BUYER'))
    owner = users.create(UserCreate(name='Seller', email='s@example.com', phone='200', password_hash=HASH, role='SELLER'))
    admin = users.create(UserCreate(name='Admin', email='a@example.com', phone='300', password_hash=HASH, role='ADMIN'))
    sellers = SellerService(db)
    seller = sellers.create(owner.id, SellerCreate(shop_name='Maker', phone='200', latitude='19', longitude='72'))
    products = ProductService(db)
    product = products.create(owner.id, seller.id, ProductCreate(name='Vase', description='Handmade', price='25.50', stock_quantity=5, category='Crafts', delivery_radius_km=2, image_url='https://example.com/vase.jpg'))
    addresses = AddressService(db)
    address = addresses.create(buyer.id, AddressCreate(label='Home', address_line1='1 Lane', city='Mumbai', state='Maharashtra', pincode='400001', latitude='19', longitude='72', is_default=True))
    return dict(users=users, buyer=buyer, owner=owner, admin=admin, sellers=sellers,
                seller=seller, products=products, product=product, addresses=addresses,
                address=address, moderation=ModerationService(db), orders=OrderService(db))


def place(m, quantity=2, **changes):
    from app.services.inputs import OrderPlacement
    m['moderation'].approve(m['admin'].id, m['product'].id)
    return m['orders'].create(OrderPlacement(buyer_id=m['buyer'].id, seller_id=m['seller'].id,
        address_id=m['address'].id, items=[dict(product_id=m['product'].id, quantity=quantity)], **changes))


def test_user_lookup_activation_and_listing(market):
    m = market
    u = m['users']
    assert u.get(m['buyer'].id).email == 'b@example.com'
    assert u.get_by_email('b@example.com').id == m['buyer'].id
    assert u.get_by_phone('100').id == m['buyer'].id
    assert u.get_by_email('absent@example.com') is None
    assert u.get_by_phone('absent') is None
    assert len(u.list()) == 3
    u.set_active(m['buyer'].id, False)
    assert not u.get(m['buyer'].id).is_active
    u.set_active(m['buyer'].id, True)
    assert u.get(m['buyer'].id).is_active


@pytest.mark.parametrize('field,value', [('email', 'b@example.com'), ('phone', '100')])
def test_duplicate_user_is_domain_error_and_session_remains_usable(db, market, field, value):
    from app.services.inputs import UserCreate
    from app.services.errors import DuplicateUser
    data = dict(name='Other', email='o@example.com', phone='400', password_hash=HASH, role='BUYER')
    with pytest.raises(DuplicateUser):
        market['users'].create(UserCreate(**{**data, field: value}))
    assert db.scalar(select(func.count()).select_from(User)) == 3
    assert market['users'].get(market['buyer'].id).is_active


def test_seller_role_uniqueness_update_and_products(market):
    from app.services.inputs import SellerCreate, SellerUpdate
    from app.services.errors import InvalidRole, DuplicateSeller
    m = market
    data = SellerCreate(shop_name='Other', phone='400', latitude=0, longitude=0)
    with pytest.raises(InvalidRole):
        m['sellers'].create(m['buyer'].id, data)
    with pytest.raises(DuplicateSeller):
        m['sellers'].create(m['owner'].id, data)
    m['sellers'].update(m['owner'].id, m['seller'].id, SellerUpdate(shop_name='New shop', description='Local'))
    assert m['sellers'].get(m['seller'].id).shop_name == 'New shop'
    assert [p.id for p in m['sellers'].list_products(m['owner'].id, m['seller'].id)] == [m['product'].id]
    with pytest.raises(ValidationError):
        SellerUpdate(is_verified=True)


def test_product_lifecycle_images_and_mappings(market):
    from app.schemas.product import ProductUpdate
    from app.services.mappers import product_response
    m = market
    p = m['product']
    assert p.status == 'PENDING' and p.is_active and p.rejection_reason is None
    assert str(product_response(p).image_url) == 'https://example.com/vase.jpg'
    m['moderation'].reject(m['admin'].id, p.id, '  Clearer photo  ')
    assert p.status == 'REJECTED' and p.rejection_reason == 'Clearer photo'
    m['products'].update(m['owner'].id, p.id, ProductUpdate(name='New vase'))
    assert p.status == 'REJECTED' and p.rejection_reason == 'Clearer photo'
    m['products'].resubmit(m['owner'].id, p.id)
    assert p.status == 'PENDING' and p.rejection_reason is None
    assert [x.id for x in m['moderation'].list_pending(m['admin'].id)] == [p.id]
    m['moderation'].approve(m['admin'].id, p.id)
    assert p.status == 'APPROVED' and p.rejection_reason is None
    m['products'].update(m['owner'].id, p.id, ProductUpdate(image_url=None))
    assert p.status == 'PENDING' and product_response(p).image_url is None
    m['products'].update(m['owner'].id, p.id, ProductUpdate(image_url='https://example.com/new.jpg'))
    assert len(p.images) == 1 and p.images[0].is_primary


@pytest.mark.parametrize('operation', ['approve', 'reject', 'resubmit'])
def test_invalid_product_transitions(market, operation):
    from app.services.errors import InvalidProductTransition
    m = market
    if operation == 'resubmit':
        with pytest.raises(InvalidProductTransition):
            m['products'].resubmit(m['owner'].id, m['product'].id)
    else:
        m['moderation'].approve(m['admin'].id, m['product'].id)
        with pytest.raises(InvalidProductTransition):
            if operation == 'approve':
                m['moderation'].approve(m['admin'].id, m['product'].id)
            else:
                m['moderation'].reject(m['admin'].id, m['product'].id, 'No')


@pytest.mark.parametrize('reason', ['', ' ', None])
def test_rejection_reason_required(market, reason):
    with pytest.raises(ValidationError):
        market['moderation'].reject(market['admin'].id, market['product'].id, reason)
    assert market['product'].status == 'PENDING'


def test_product_and_moderation_ownership(market):
    from app.schemas.product import ProductUpdate
    from app.services.errors import OwnershipError, InvalidRole, InactiveUser
    m = market
    with pytest.raises(OwnershipError):
        m['products'].update(m['buyer'].id, m['product'].id, ProductUpdate(name='Stolen'))
    with pytest.raises(OwnershipError):
        m['products'].set_active(m['buyer'].id, m['product'].id, False)
    with pytest.raises(InvalidRole):
        m['moderation'].approve(m['owner'].id, m['product'].id)
    m['users'].set_active(m['owner'].id, False)
    with pytest.raises(InactiveUser):
        m['products'].update(m['owner'].id, m['product'].id, ProductUpdate(name='Inactive'))


@pytest.mark.parametrize('status,active,stock,visible', [
    ('PENDING', True, 1, False), ('REJECTED', True, 1, False),
    ('APPROVED', False, 1, False), ('APPROVED', True, 0, False),
    ('APPROVED', True, 1, True)])
def test_candidate_visibility(db, market, status, active, stock, visible):
    p = market['product']
    p.status, p.is_active, p.stock_quantity = status, active, stock
    p.rejection_reason = 'Reason' if status == 'REJECTED' else None
    db.flush()
    assert bool(market['products'].list_buyer_candidates_without_geography()) is visible


def test_activation_does_not_approve(market):
    m = market
    m['products'].set_active(m['owner'].id, m['product'].id, False)
    assert not m['product'].is_active
    m['products'].set_active(m['owner'].id, m['product'].id, True)
    assert m['product'].status == 'PENDING'


def test_address_default_update_ownership_and_order_history(db, market):
    from app.services.inputs import AddressCreate, AddressUpdate
    from app.services.errors import AddressOwnershipError, AddressInUse
    m = market
    a = m['addresses'].create(m['buyer'].id, AddressCreate(label='Work', address_line1='2 Lane', city='Mumbai', state='Maharashtra', pincode='400001', latitude=0, longitude=0, is_default=True))
    assert not m['address'].is_default and a.is_default
    assert len(m['addresses'].list(m['buyer'].id)) == 2
    m['addresses'].set_default(m['buyer'].id, m['address'].id)
    assert not a.is_default and m['address'].is_default
    m['addresses'].update(m['buyer'].id, a.id, AddressUpdate(city='Pune', address_line2='Floor 2'))
    assert a.city == 'Pune'
    with pytest.raises(AddressOwnershipError):
        m['addresses'].get(m['owner'].id, a.id)
    with pytest.raises(AddressOwnershipError):
        m['addresses'].update(m['owner'].id, a.id, AddressUpdate(label='Stolen'))
    place(m)
    with pytest.raises(AddressInUse):
        m['addresses'].update(m['buyer'].id, m['address'].id, AddressUpdate(city='Delhi'))
    m['addresses'].update(m['buyer'].id, m['address'].id, AddressUpdate(label='Old home', is_default=False))
    assert m['address'].label == 'Old home'
    assert db.scalar(select(func.count()).select_from(Address).where(Address.is_default)) == 0


def test_successful_order_snapshots_stock_and_response(db, market):
    from app.services.mappers import order_response
    from app.schemas.product import ProductUpdate
    m = market
    order = place(m)
    assert order.status == 'PLACED' and order.subtotal == Decimal('51.00')
    assert order.delivery_fee == Decimal('0.00') and order.total_amount == Decimal('51.00')
    assert m['product'].stock_quantity == 3
    assert order.items[0].product_name == 'Vase' and order.items[0].unit_price == Decimal('25.50')
    m['products'].update(m['owner'].id, m['product'].id, ProductUpdate(name='Renamed', price='99.00'))
    response = order_response(m['orders'].get(m['buyer'].id, order.id))
    assert response.items[0].name == 'Vase' and response.items[0].unit_price == Decimal('25.50')
    assert response.total == Decimal('51.00')
    assert len(m['orders'].list_for_buyer(m['buyer'].id)) == 1
    assert len(m['orders'].list_for_seller(m['owner'].id, m['seller'].id)) == 1


@pytest.mark.parametrize('problem,error_name', [
    ('stock', 'InsufficientStock'), ('pending', 'ProductUnavailable'),
    ('inactive_product', 'ProductUnavailable'), ('inactive_buyer', 'InactiveUser'),
    ('inactive_seller', 'InactiveUser'), ('address', 'AddressOwnershipError'),
    ('wrong_buyer_role', 'InvalidRole'), ('seller', 'SellerNotFound'),
    ('product', 'ProductNotFound'), ('buyer', 'UserNotFound')])
def test_order_failures_are_atomic(db, market, problem, error_name):
    from app.services.inputs import OrderPlacement
    from app.services import errors
    m = market
    p = m['product']
    m['moderation'].approve(m['admin'].id, p.id)
    data = dict(buyer_id=m['buyer'].id, seller_id=m['seller'].id, address_id=m['address'].id,
                items=[dict(product_id=p.id, quantity=2)])
    if problem == 'stock':
        data['items'][0]['quantity'] = 6
    elif problem == 'pending':
        p.status = 'PENDING'
    elif problem == 'inactive_product':
        p.is_active = False
    elif problem == 'inactive_buyer':
        m['buyer'].is_active = False
    elif problem == 'inactive_seller':
        m['owner'].is_active = False
    elif problem == 'address':
        data['buyer_id'] = m['owner'].id
        m['owner'].role = 'BUYER'
    elif problem == 'wrong_buyer_role':
        m['buyer'].role = 'ADMIN'
    elif problem == 'seller':
        data['seller_id'] = 999999
    elif problem == 'product':
        data['items'][0]['product_id'] = 999999
    elif problem == 'buyer':
        data['buyer_id'] = 999999
    db.flush()
    with pytest.raises(getattr(errors, error_name)):
        m['orders'].create(OrderPlacement(**data))
    assert db.scalar(select(func.count()).select_from(Order)) == 0
    assert db.scalar(select(func.count()).select_from(OrderItem)) == 0
    assert m['products'].get(p.id).stock_quantity == 5


@pytest.mark.parametrize('items', [[], [{'product_id': 1, 'quantity': 0}], [{'product_id': 1, 'quantity': True}], [{'product_id': 1, 'quantity': 1}, {'product_id': 1, 'quantity': 2}]])
def test_invalid_order_input(items):
    from app.services.inputs import OrderPlacement
    with pytest.raises(ValidationError):
        OrderPlacement(buyer_id=1, seller_id=1, address_id=1, items=items)


def test_order_forward_transitions_and_terminal_protection(market):
    from app.services.errors import InvalidOrderTransition, OwnershipError
    m = market
    order = place(m)
    with pytest.raises(OwnershipError):
        m['orders'].transition(m['admin'].id, order.id, 'ACCEPTED')
    for status in ['ACCEPTED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED']:
        assert m['orders'].transition(m['owner'].id, order.id, status).status == status
    with pytest.raises(InvalidOrderTransition):
        m['orders'].transition(m['owner'].id, order.id, 'PREPARING')


@pytest.mark.parametrize('terminal,actor,accepted', [('CANCELLED', 'buyer', False), ('CANCELLED', 'owner', True), ('REJECTED', 'owner', False)])
def test_terminal_restocks_once(market, terminal, actor, accepted):
    from app.services.errors import InvalidOrderTransition
    m = market
    order = place(m)
    if accepted:
        m['orders'].transition(m['owner'].id, order.id, 'ACCEPTED')
    m['orders'].transition(m[actor].id, order.id, terminal)
    assert m['products'].get(m['product'].id).stock_quantity == 5
    with pytest.raises(InvalidOrderTransition):
        m['orders'].transition(m[actor].id, order.id, terminal)
    assert m['products'].get(m['product'].id).stock_quantity == 5


def test_buyer_cannot_progress_or_reject_and_cannot_cancel_preparing(market):
    from app.services.errors import OwnershipError, InvalidOrderTransition
    m = market
    order = place(m)
    for status in ['ACCEPTED', 'REJECTED']:
        with pytest.raises(OwnershipError):
            m['orders'].transition(m['buyer'].id, order.id, status)
    m['orders'].transition(m['owner'].id, order.id, 'ACCEPTED')
    m['orders'].transition(m['owner'].id, order.id, 'PREPARING')
    with pytest.raises(InvalidOrderTransition):
        m['orders'].transition(m['buyer'].id, order.id, 'CANCELLED')
    assert m['products'].get(m['product'].id).stock_quantity == 3
