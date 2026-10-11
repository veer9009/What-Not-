from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Numeric, String, Text, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.seller_profile import SellerProfile
    from app.models.product_image import ProductImage
    from app.models.order_item import OrderItem


class Product(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("id", "seller_id", name="uq_products_id_seller_id"),
        CheckConstraint("price >= 0 AND price != 'NaN'::numeric", name="price"),
        CheckConstraint("stock_quantity >= 0", name="stock_quantity"),
        CheckConstraint("delivery_radius_km IN (1,2,3)", name="delivery_radius_km"),
        CheckConstraint("status IN ('PENDING','APPROVED','REJECTED')", name="status"),
    )

    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("seller_profiles.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock_quantity: Mapped[int]
    category: Mapped[str] = mapped_column(String(80))
    delivery_radius_km: Mapped[int]
    status: Mapped[str] = mapped_column(String(10), server_default="PENDING")
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(server_default=true())
    seller: Mapped[SellerProfile] = relationship(back_populates="products")
    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product", cascade="all, delete-orphan", passive_deletes=True,
        order_by="ProductImage.sort_order",
    )
    order_items: Mapped[list[OrderItem]] = relationship(
        back_populates="product", foreign_keys="OrderItem.product_id", passive_deletes="all",
        primaryjoin="and_(Product.id == OrderItem.product_id, Product.seller_id == OrderItem.seller_id)",
    )
