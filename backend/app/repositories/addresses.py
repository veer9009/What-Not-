from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Address, Order
from app.repositories.validation import database_id


class AddressRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, address_id: int, *, lock=False):
        query = select(Address).where(Address.id == database_id(address_id))
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(query)

    def for_user(self, user_id: int):
        return list(self.session.scalars(select(Address).where(Address.user_id == database_id(user_id)).order_by(Address.id)))

    def clear_default(self, user_id: int):
        self.session.execute(update(Address).where(Address.user_id == database_id(user_id), Address.is_default.is_(True))
                             .values(is_default=False))
        self.session.flush()

    def referenced(self, address_id: int):
        return self.session.scalar(select(Order.id).where(Order.address_id == database_id(address_id)).limit(1)) is not None

    def add(self, address: Address):
        self.session.add(address)
        return address
