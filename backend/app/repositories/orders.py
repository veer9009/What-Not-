from hashlib import sha256

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models import Order
from app.repositories.validation import database_id


class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, order_id: int, *, lock=False):
        query = select(Order).where(Order.id == database_id(order_id)).options(selectinload(Order.items))
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(query)

    def lock_idempotency(self, buyer_id, key):
        # Database transaction lock, shared by all API workers. Hash collisions only
        # serialize unrelated requests; lookup and the unique constraint remain exact.
        scope = f'order-placement:{database_id(buyer_id)}:{key}'
        lock_id = int.from_bytes(sha256(scope.encode()).digest()[:8], 'big', signed=True)
        self.session.execute(text('SELECT pg_advisory_xact_lock(:lock_id)'), {'lock_id': lock_id})

    def for_idempotency(self, buyer_id, key):
        return self.session.scalar(select(Order).where(Order.buyer_id == database_id(buyer_id),
            Order.idempotency_key == key).options(selectinload(Order.items))
            .execution_options(populate_existing=True))

    def for_buyer(self, buyer_id: int, offset: int, limit: int):
        return list(self.session.scalars(select(Order).where(Order.buyer_id == database_id(buyer_id))
            .options(selectinload(Order.items)).order_by(Order.id.desc()).offset(offset).limit(limit)))

    def for_seller(self, seller_id: int, offset: int, limit: int):
        return list(self.session.scalars(select(Order).where(Order.seller_id == database_id(seller_id))
            .options(selectinload(Order.items)).order_by(Order.id.desc()).offset(offset).limit(limit)))

    def add(self, order: Order):
        self.session.add(order)
        return order
