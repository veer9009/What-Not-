from decimal import Decimal

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.models import Order, OrderItem
from app.repositories.orders import OrderRepository
from app.repositories.products import ProductRepository
from app.schemas.common import MAX_INTEGER, MAX_MONEY, Money
from app.schemas.order import OrderStatus
from app.services.addresses import owned_address
from app.services.errors import (AmountOverflow, InsufficientStock, InvalidOrderTransition,
    OrderNotFound, OwnershipError, ProductNotFound, ProductUnavailable)
from app.services.inputs import OrderPlacement
from app.services.operations import write_operation
from app.services.sellers import owned_seller, require_seller
from app.services.users import pagination, require_user

TRANSITIONS = {
    'PLACED': frozenset({'ACCEPTED', 'CANCELLED', 'REJECTED'}),
    'ACCEPTED': frozenset({'PREPARING', 'CANCELLED'}),
    'PREPARING': frozenset({'OUT_FOR_DELIVERY'}),
    'OUT_FOR_DELIVERY': frozenset({'DELIVERED'}),
    'DELIVERED': frozenset(), 'CANCELLED': frozenset(), 'REJECTED': frozenset(),
}


class DeliveryFeePolicy:
    """Trusted fixed fee; provisional zero, independent of frontend demo fees."""
    def __init__(self, fixed_fee: Decimal | str = Decimal('0.00')):
        self.fixed_fee = TypeAdapter(Money).validate_python(fixed_fee)

    def calculate(self) -> Decimal:
        return self.fixed_fee


class OrderService:
    def __init__(self, session: Session, fee_policy: DeliveryFeePolicy | None = None):
        self.session = session
        self.repository = OrderRepository(session)
        self.products = ProductRepository(session)
        self.fee_policy = fee_policy or DeliveryFeePolicy()

    @write_operation
    def create(self, data: OrderPlacement):
        """Atomic inventory reservation; geographic eligibility is NOT implemented."""
        data = OrderPlacement.model_validate(data)
        require_user(self.session, data.buyer_id, role='BUYER', lock='shared')
        owned_address(self.session, data.buyer_id, data.address_id, lock=True)
        seller = require_seller(self.session, data.seller_id)
        require_user(self.session, seller.user_id, role='SELLER', lock='shared')
        products = self.products.lock_many([item.product_id for item in data.items])
        by_id = {product.id: product for product in products}
        if len(by_id) != len(data.items):
            raise ProductNotFound('A requested product does not exist')
        subtotal = Decimal('0.00')
        items = []
        for requested in data.items:
            product = by_id[requested.product_id]
            if product.seller_id != data.seller_id:
                raise OwnershipError('Every product must belong to the order seller')
            if product.status != 'APPROVED' or not product.is_active or product.stock_quantity <= 0 or product.price <= 0:
                raise ProductUnavailable('Product is unavailable for purchase')
            if requested.quantity > product.stock_quantity:
                raise InsufficientStock('Requested quantity exceeds available stock')
            subtotal += product.price * requested.quantity
            items.append(OrderItem(product_id=product.id, seller_id=data.seller_id,
                product_name=product.name, unit_price=product.price, quantity=requested.quantity))
        delivery_fee = TypeAdapter(Money).validate_python(self.fee_policy.calculate())
        total = subtotal + delivery_fee
        if subtotal > MAX_MONEY or total > MAX_MONEY:
            raise AmountOverflow('Order amounts exceed the supported monetary range')
        order = Order(buyer_id=data.buyer_id, seller_id=data.seller_id, address_id=data.address_id,
            status='PLACED', subtotal=subtotal, delivery_fee=delivery_fee, total_amount=total, items=items)
        self.repository.add(order)
        for requested in data.items:
            by_id[requested.product_id].stock_quantity -= requested.quantity
        return order

    def _owned(self, actor, order):
        if actor.id == order.buyer_id and actor.role == 'BUYER':
            return 'BUYER'
        seller = require_seller(self.session, order.seller_id)
        if actor.id == seller.user_id and actor.role == 'SELLER':
            return 'SELLER'
        raise OwnershipError('Order belongs to another buyer or seller')

    def get(self, actor_id: int, order_id: int):
        actor = require_user(self.session, actor_id)
        order = self.repository.get(order_id)
        if order is None:
            raise OrderNotFound('Order does not exist')
        self._owned(actor, order)
        return order

    def list_for_buyer(self, buyer_id: int, *, offset=0, limit=100):
        require_user(self.session, buyer_id, role='BUYER')
        return self.repository.for_buyer(buyer_id, *pagination(offset, limit))

    def list_for_seller(self, actor_id: int, seller_id: int, *, offset=0, limit=100):
        owned_seller(self.session, actor_id, seller_id)
        return self.repository.for_seller(seller_id, *pagination(offset, limit))

    @write_operation
    def transition(self, actor_id: int, order_id: int, new_status: OrderStatus | str):
        new_status = TypeAdapter(OrderStatus).validate_python(new_status).value
        actor = require_user(self.session, actor_id, lock=True)
        order = self.repository.get(order_id, lock=True)
        if order is None:
            raise OrderNotFound('Order does not exist')
        role = self._owned(actor, order)
        if role == 'BUYER' and new_status != 'CANCELLED':
            raise OwnershipError('Buyers may only cancel eligible orders')
        if new_status not in TRANSITIONS[order.status]:
            raise InvalidOrderTransition('Order cannot transition to the requested status')
        if new_status in {'CANCELLED', 'REJECTED'}:
            products = self.products.lock_many([item.product_id for item in order.items])
            by_id = {product.id: product for product in products}
            if len(by_id) != len(order.items):
                raise ProductNotFound('An order product does not exist')
            for item in order.items:
                if by_id[item.product_id].stock_quantity + item.quantity > MAX_INTEGER:
                    raise AmountOverflow('Restored inventory exceeds the supported stock range')
            for item in order.items:
                by_id[item.product_id].stock_quantity += item.quantity
        order.status = new_status
        return order
