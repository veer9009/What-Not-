from decimal import Decimal
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.models.events import AuditEvent
from app.services.notifications import publish_event
from app.core.config import Settings
from hashlib import sha256
import json

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.models import Order, OrderItem
from app.repositories.orders import OrderRepository
from app.repositories.products import ProductRepository
from app.schemas.common import MAX_INTEGER, MAX_MONEY, Money
from app.schemas.order import OrderStatus
from app.services.addresses import owned_address
from app.services.errors import (AmountOverflow, DeliveryIneligible, IdempotencyConflict, InsufficientStock, InvalidOrderTransition,
    OrderNotFound, OwnershipError, ProductNotFound, ProductUnavailable)
from app.services.inputs import OrderPlacement
from app.services.geography import distance_km, within_radius
from app.services.operations import write_operation
from app.services.sellers import owned_seller, require_seller
from app.services.users import pagination, require_user

TRANSITIONS = {
    'PLACED': frozenset({'ACCEPTED', 'CANCELLED', 'REJECTED'}),
    'ACCEPTED': frozenset({'PREPARING', 'CANCELLED'}),
    'PREPARING': frozenset({'OUT_FOR_DELIVERY'}),
    'OUT_FOR_DELIVERY': frozenset({'DELIVERED'}),
    'DELIVERED': frozenset({'COMPLETED', 'DELIVERY_DISPUTED'}),
    'COMPLETED': frozenset(), 'DELIVERY_DISPUTED': frozenset(), 'CANCELLED': frozenset(), 'REJECTED': frozenset(),
}


class DeliveryFeePolicy:
    """Trusted fixed fee; provisional zero, independent of frontend demo fees."""
    def __init__(self, fixed_fee: Decimal | str = Decimal('0.00')):
        self.fixed_fee = TypeAdapter(Money).validate_python(fixed_fee)

    def calculate(self) -> Decimal:
        return self.fixed_fee


class OrderService:
    def __init__(self, session: Session, fee_policy: DeliveryFeePolicy | None = None, settings=None,
                 require_price_confirmation=False):
        self.require_price_confirmation = require_price_confirmation
        self._settings_provided = settings is not None
        self.settings = settings or Settings(_env_file=None)
        self.session = session
        self.repository = OrderRepository(session)
        self.products = ProductRepository(session)
        self.fee_policy = fee_policy or DeliveryFeePolicy()

    @write_operation
    def create(self, data: OrderPlacement):
        """Atomic placement with locked inventory and authoritative delivery eligibility."""
        data = OrderPlacement.model_validate(data)
        require_user(self.session, data.buyer_id, role='BUYER', lock='shared')
        fingerprint = None
        if data.idempotency_key is not None:
            logical_request = dict(address_id=data.address_id, seller_id=data.seller_id,
                items=[item.model_dump(mode='json', exclude_none=True) for item in sorted(data.items, key=lambda item: item.product_id)])
            fingerprint = sha256(json.dumps(logical_request, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            self.repository.lock_idempotency(data.buyer_id, data.idempotency_key)
            existing = self.repository.for_idempotency(data.buyer_id, data.idempotency_key)
            if existing is not None:
                if existing.request_fingerprint != fingerprint:
                    raise IdempotencyConflict('This idempotency key was already used for a different order request')
                # A replay returns the purchase snapshot, even if stock/location has changed.
                return existing
        if self.require_price_confirmation and any(item.expected_unit_price is None for item in data.items):
            raise ProductUnavailable('Review and confirm the current price for every item before ordering')
        if self._settings_provided and self.settings.environment != 'test':
            from app.services.abuse import check_action_limit
            check_action_limit(self.session, self.settings, 'checkout', data.buyer_id)
        address = owned_address(self.session, data.buyer_id, data.address_id, lock=True)
        seller = require_seller(self.session, data.seller_id)
        require_user(self.session, seller.user_id, role='SELLER', lock='shared')
        # Match seller writes' user-before-profile lock order; refresh cached coordinates.
        seller = require_seller(self.session, data.seller_id, lock='shared')
        if seller.dispatch_location_confirmed_at is None:
            raise ProductUnavailable('Seller dispatch location must be confirmed before ordering')
        distance = distance_km(address.latitude, address.longitude, seller.latitude, seller.longitude)
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
            if not within_radius(distance, product.delivery_radius_km):
                raise DeliveryIneligible('This product is outside the selected delivery address.')
            if product.status != 'APPROVED' or not product.is_active or product.stock_quantity <= 0 or product.price <= 0:
                raise ProductUnavailable('Product is unavailable for purchase')
            if requested.expected_unit_price is not None and requested.expected_unit_price != product.price:
                raise ProductUnavailable('Product price changed; review the current price before ordering')
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
            idempotency_key=data.idempotency_key, request_fingerprint=fingerprint,
            status='PLACED', subtotal=subtotal, delivery_fee=delivery_fee, total_amount=total, items=items)
        self.repository.add(order)
        for requested in data.items:
            by_id[requested.product_id].stock_quantity -= requested.quantity
        self.session.flush()
        self._record(order, None, 'PLACED', data.buyer_id, 'PLACED')
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
        if role == 'BUYER' and new_status not in {'CANCELLED', 'COMPLETED', 'DELIVERY_DISPUTED'}:
            raise OwnershipError('Buyers may only cancel eligible orders or confirm receipt')
        if role == 'SELLER' and new_status in {'COMPLETED', 'DELIVERY_DISPUTED'}:
            raise OwnershipError('Only the owning buyer may confirm receipt')
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
        self._record(order, order.status, new_status, actor_id, 'USER_TRANSITION')
        return order

    def _record(self, order, previous, status, actor_id, reason, *, source=None):
        now = datetime.now(timezone.utc)
        order.status = status
        if status == 'DELIVERED':
            order.delivered_at = now
            order.confirmation_deadline = now + timedelta(hours=self.settings.delivery_confirmation_grace_hours)
        if status == 'COMPLETED':
            order.completed_at = now
            order.completion_source = source or 'BUYER'
        self.session.add(AuditEvent(actor_id=actor_id, actor_type='USER' if actor_id else 'SYSTEM',
            entity_type='order', entity_id=order.id, action='ORDER_TRANSITION',
            previous_status=previous, next_status=status, reason=reason))
        seller = require_seller(self.session, order.seller_id)
        for recipient in {order.buyer_id, seller.user_id}:
            body = ('Delivery was marked complete. Confirm receipt or report a delivery problem before the confirmation deadline.'
                if status == 'DELIVERED' and recipient == order.buyer_id else f'Order status: {status}.')
            publish_event(self.session, recipient, f'order:{order.id}:{status}', 'ORDER_STATUS',
                'order', order.id, 'Order update', body)

    @write_operation
    def auto_complete_due(self, *, limit=None, now=None):
        now = now or datetime.now(timezone.utc)
        limit = self.settings.outbox_batch_size if limit is None else limit
        if not 1 <= limit <= 1000:
            raise ValueError('Batch limit must be between 1 and 1000')
        rows = list(self.session.scalars(select(Order).where(Order.status == 'DELIVERED',
            Order.confirmation_deadline <= now).order_by(Order.confirmation_deadline, Order.id)
            .limit(limit).with_for_update(skip_locked=True).execution_options(populate_existing=True)))
        count = 0
        for order in rows:
            if order.status == 'DELIVERED' and order.confirmation_deadline is not None and order.confirmation_deadline <= now:
                self._record(order, 'DELIVERED', 'COMPLETED', None, 'GRACE_EXPIRED', source='TIMEOUT')
                count += 1
        return count

    def fulfillment(self, actor_id, order_id, reason=None):
        actor = require_user(self.session, actor_id)
        order = self.repository.get(order_id)
        if order is None:
            raise OrderNotFound('Order does not exist')
        if actor.role == 'ADMIN':
            if not reason or not reason.strip() or len(reason) > 1000:
                raise OwnershipError('A bounded investigation reason is required')
            self.session.add(AuditEvent(actor_id=actor_id, entity_type='order', entity_id=order.id,
                action='FULFILLMENT_READ', reason=reason.strip()))
        else:
            role = self._owned(actor, order)
            if role == 'SELLER' and order.status not in {'ACCEPTED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'DELIVERY_DISPUTED'}:
                raise OwnershipError('Fulfillment information is unavailable for this order status')
        address = order.address
        return dict(recipient_name=order.buyer.name, phone=order.buyer.phone,
            address_line1=address.address_line1, address_line2=address.address_line2,
            city=address.city, state=address.state, pincode=address.pincode)

    @write_operation
    def admin_resolve(self, actor_id, order_id, action, reason):
        require_user(self.session, actor_id, role='ADMIN', lock=True)
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
            raise InvalidOrderTransition('An investigation reason is required')
        order = self.repository.get(order_id, lock=True)
        if order is None:
            raise OrderNotFound('Order does not exist')
        previous = order.status
        if action in {'COMPLETE_DISPUTE', 'CANCEL_DISPUTE'} and previous == 'DELIVERY_DISPUTED':
            status = 'COMPLETED' if action == 'COMPLETE_DISPUTE' else 'CANCELLED'
        elif action == 'CANCEL_STRANDED' and previous in {'PLACED', 'ACCEPTED'}:
            seller = require_seller(self.session, order.seller_id)
            from app.models import User
            parties = list(self.session.scalars(select(User).where(User.id.in_([order.buyer_id, seller.user_id]))))
            if all(user.is_active for user in parties):
                raise InvalidOrderTransition('Order must be stranded by a suspended participant')
            products = {p.id: p for p in self.products.lock_many([i.product_id for i in order.items])}
            for item in order.items:
                if products[item.product_id].stock_quantity + item.quantity > MAX_INTEGER:
                    raise AmountOverflow('Restored inventory exceeds the supported stock range')
                products[item.product_id].stock_quantity += item.quantity
            status = 'CANCELLED'
        elif action == 'CANCEL_INVESTIGATED' and previous in {'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED'}:
            status = 'CANCELLED'
        else:
            raise InvalidOrderTransition('Investigated action is unavailable for this state')
        disposition = 'RESTORED' if action == 'CANCEL_STRANDED' else 'NO_RESTOCK'
        self._record(order, previous, status, actor_id, f'{action}:{disposition}: {reason.strip()}', source='ADMIN')
        return order
