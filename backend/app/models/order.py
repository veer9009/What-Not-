from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.seller_profile import SellerProfile
    from app.models.address import Address
    from app.models.order_item import OrderItem


class Order(IdMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("id", "seller_id", name="uq_orders_id_seller_id"),
        CheckConstraint("status IN ('PLACED','ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','CANCELLED','REJECTED')", name="status"),
        CheckConstraint("subtotal >= 0 AND subtotal != 'NaN'::numeric", name="subtotal"),
        CheckConstraint("delivery_fee >= 0 AND delivery_fee != 'NaN'::numeric", name="delivery_fee"),
        CheckConstraint("total_amount >= 0 AND total_amount != 'NaN'::numeric", name="total_amount"),
    )

    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("seller_profiles.id", ondelete="RESTRICT"), index=True)
    address_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("addresses.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), server_default="PLACED")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    buyer: Mapped[User] = relationship(back_populates="orders")
    seller: Mapped[SellerProfile] = relationship(back_populates="orders")
    address: Mapped[Address] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan", passive_deletes=True)
