from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, ForeignKey, DateTime, Numeric, UniqueConstraint, CheckConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, IdMixin, TimestampMixin

class PropertyProfile(IdMixin, TimestampMixin, Base):
    __tablename__ = 'property_profiles'
    __table_args__ = (CheckConstraint("capacity IN ('OWNER','AGENT')", name='capacity'),)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    capacity: Mapped[str] = mapped_column(String(10))
    share_contact: Mapped[bool] = mapped_column(Boolean, default=False)

class PropertyListing(IdMixin, TimestampMixin, Base):
    __tablename__ = 'property_listings'
    __table_args__ = (CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','SOLD','HIDDEN')", name='status'), CheckConstraint('price > 0', name='positive_price'), CheckConstraint("category IN ('Residential','Commercial','Land/Plots')", name='category'))
    creator_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    capacity: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))
    price: Mapped[Decimal] = mapped_column(Numeric(12,2))
    locality: Mapped[str] = mapped_column(String(120))
    private_address: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default='PENDING', index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    reconfirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

class PropertyEnquiry(IdMixin, TimestampMixin, Base):
    __tablename__ = 'property_enquiries'
    property_id: Mapped[int] = mapped_column(ForeignKey('property_listings.id'), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    message: Mapped[str] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default='OPEN')

class PropertyVisit(IdMixin, TimestampMixin, Base):
    __tablename__ = 'property_visits'
    __table_args__ = (CheckConstraint("status IN ('PENDING','ALTERNATE','CONFIRMED','REJECTED','CANCELLED','SUSPENDED')", name='status'),)
    property_id: Mapped[int] = mapped_column(ForeignKey('property_listings.id'), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12), default='PENDING')
    reason: Mapped[str | None] = mapped_column(Text)

class SavedProperty(IdMixin, TimestampMixin, Base):
    __tablename__ = 'saved_properties'
    __table_args__ = (UniqueConstraint('buyer_id','property_id'),)
    buyer_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    property_id: Mapped[int] = mapped_column(ForeignKey('property_listings.id'))

class PropertyReport(IdMixin, TimestampMixin, Base):
    __tablename__ = 'property_reports'
    property_id: Mapped[int] = mapped_column(ForeignKey('property_listings.id'), index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    reason: Mapped[str] = mapped_column(String(40))
    explanation: Mapped[str] = mapped_column(Text)
    disposition: Mapped[str] = mapped_column(String(12), default='OPEN')
    resolution_reason: Mapped[str | None] = mapped_column(Text)
