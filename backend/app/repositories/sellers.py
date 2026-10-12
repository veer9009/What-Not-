from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SellerProfile
from app.repositories.validation import database_id


class SellerRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, seller_id: int, *, lock=False):
        query = select(SellerProfile).where(SellerProfile.id == database_id(seller_id))
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(query)

    def by_user(self, user_id: int):
        return self.session.scalar(select(SellerProfile).where(SellerProfile.user_id == database_id(user_id)))

    def add(self, seller: SellerProfile):
        self.session.add(seller)
        return seller
