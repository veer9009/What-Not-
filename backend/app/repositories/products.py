from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, joinedload

from app.models import Product, SellerProfile, User
from app.repositories.validation import database_id


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, product_id: int, *, lock=False):
        query = select(Product).where(Product.id == database_id(product_id)).options(selectinload(Product.images))
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(query)

    def lock_many(self, ids: list[int]):
        ids = [database_id(value) for value in ids]
        return list(self.session.scalars(select(Product).where(Product.id.in_(ids))
            .order_by(Product.id).with_for_update().execution_options(populate_existing=True)))

    def for_seller(self, seller_id: int, offset: int, limit: int):
        return list(self.session.scalars(select(Product).where(Product.seller_id == database_id(seller_id))
            .options(selectinload(Product.images)).order_by(Product.id).offset(offset).limit(limit)))

    def pending(self, offset: int, limit: int):
        return list(self.session.scalars(select(Product).where(Product.status == 'PENDING')
            .options(selectinload(Product.images)).order_by(Product.id).offset(offset).limit(limit)))

    def buyer_candidates_without_geography(self, offset: int, limit: int):
        return list(self.session.scalars(select(Product).where(Product.status == 'APPROVED',
            Product.is_active.is_(True), Product.stock_quantity > 0)
            .options(selectinload(Product.images)).order_by(Product.id).offset(offset).limit(limit)))

    def add(self, product: Product):
        self.session.add(product)
        return product

    def _discovery_query(self):
        return (select(Product).join(Product.seller).join(SellerProfile.user)
                .where(Product.status == 'APPROVED', Product.is_active.is_(True),
                       Product.stock_quantity > 0, SellerProfile.dispatch_location_confirmed_at.is_not(None),
                       User.is_active.is_(True), User.role == 'SELLER')
                .options(selectinload(Product.images), joinedload(Product.seller))
                .execution_options(populate_existing=True))

    def discovery_candidates(self, after_id: int, limit: int = 100):
        return list(self.session.scalars(self._discovery_query()
                    .where(Product.id > after_id).order_by(Product.id).limit(limit)))

    def eligible_detail(self, product_id: int):
        return self.session.scalar(self._discovery_query().where(Product.id == database_id(product_id)))
