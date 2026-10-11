from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, CheckConstraint, ForeignKeyConstraint, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, IdMixin

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.product import Product


class OrderItem(IdMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        ForeignKeyConstraint(["order_id", "seller_id"], ["orders.id", "orders.seller_id"],
                             name="fk_order_items_order_seller", ondelete="CASCADE"),
        ForeignKeyConstraint(["product_id", "seller_id"], ["products.id", "products.seller_id"],
                             name="fk_order_items_product_seller", ondelete="RESTRICT"),
        UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
        CheckConstraint("quantity > 0", name="quantity"),
        CheckConstraint("unit_price >= 0 AND unit_price != 'NaN'::numeric", name="unit_price"),
    )

    order_id: Mapped[int] = mapped_column(BigInteger)
    product_id: Mapped[int] = mapped_column(BigInteger, index=True)
    seller_id: Mapped[int] = mapped_column(BigInteger)
    product_name: Mapped[str] = mapped_column(String(120))
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order: Mapped[Order] = relationship(back_populates="items")
    # Only product_id is writable here; order controls the shared seller_id.
    product: Mapped[Product] = relationship(
        back_populates="order_items", foreign_keys=[product_id],
        primaryjoin="and_(OrderItem.product_id == Product.id, OrderItem.seller_id == Product.seller_id)",
    )
