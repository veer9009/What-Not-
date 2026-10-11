from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Numeric, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product
    from app.models.order import Order


class SellerProfile(IdMixin, TimestampMixin, Base):
    __tablename__ = "seller_profiles"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude"),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), unique=True)
    shop_name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(String(32))
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    is_verified: Mapped[bool] = mapped_column(server_default=false())
    user: Mapped[User] = relationship(back_populates="seller_profile")
    products: Mapped[list[Product]] = relationship(back_populates="seller", passive_deletes="all")
    orders: Mapped[list[Order]] = relationship(back_populates="seller", passive_deletes="all")
