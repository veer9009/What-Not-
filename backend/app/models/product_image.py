from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Text, false, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, CreatedMixin, IdMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ProductImage(IdMixin, CreatedMixin, Base):
    __tablename__ = "product_images"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order"),
        Index("ix_product_images_product_sort", "product_id", "sort_order"),
        Index("uq_product_images_primary", "product_id", unique=True, postgresql_where=text("is_primary")),
    )

    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"))
    image_url: Mapped[str] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(server_default=false())
    sort_order: Mapped[int] = mapped_column(server_default="0")
    product: Mapped[Product] = relationship(back_populates="images")
