from sqlalchemy import select
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

    def for_buyer(self, buyer_id: int, offset: int, limit: int):
        return list(self.session.scalars(select(Order).where(Order.buyer_id == database_id(buyer_id))
            .options(selectinload(Order.items)).order_by(Order.id).offset(offset).limit(limit)))

    def for_seller(self, seller_id: int, offset: int, limit: int):
        return list(self.session.scalars(select(Order).where(Order.seller_id == database_id(seller_id))
            .options(selectinload(Order.items)).order_by(Order.id).offset(offset).limit(limit)))

    def add(self, order: Order):
        self.session.add(order)
        return order
