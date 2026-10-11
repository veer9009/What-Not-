from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.address import Address
    from app.models.order import Order
    from app.models.seller_profile import SellerProfile


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('BUYER','SELLER','ADMIN')", name="role"),)

    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(server_default=true())
    seller_profile: Mapped[SellerProfile | None] = relationship(back_populates="user", passive_deletes="all")
    addresses: Mapped[list[Address]] = relationship(back_populates="user", passive_deletes="all")
    orders: Mapped[list[Order]] = relationship(back_populates="buyer", passive_deletes="all")
