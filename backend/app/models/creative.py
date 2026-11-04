from decimal import Decimal
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, IdMixin, TimestampMixin, CreatedMixin

class CreativeProvider(IdMixin, TimestampMixin, Base):
    __tablename__ = 'creative_providers'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    bio: Mapped[str] = mapped_column(Text)

class CreativeListing(IdMixin, TimestampMixin, Base):
    __tablename__ = 'creative_listings'
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','TAKEN_DOWN')", name='status'),
        CheckConstraint("pricing IN ('FIXED','STARTING','HOURLY','QUOTATION')", name='pricing'),
        CheckConstraint("(pricing='QUOTATION' AND amount IS NULL) OR (pricing<>'QUOTATION' AND amount IS NOT NULL AND amount>0)", name='amount'),
        CheckConstraint("category IN ('Video Editing','Travel Video Editing','Influencer Reel Editing','VFX')", name='category'),
        CheckConstraint("currency='INR'", name='currency'),
        CheckConstraint('remote OR locality IS NOT NULL', name='service_area'),
    )
    provider_id: Mapped[int] = mapped_column(ForeignKey('creative_providers.id', ondelete='RESTRICT'), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40))
    pricing: Mapped[str] = mapped_column(String(12))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12,2))
    currency: Mapped[str] = mapped_column(String(3), default='INR')
    remote: Mapped[bool] = mapped_column(Boolean)
    locality: Mapped[str | None] = mapped_column(String(160))
    portfolio: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(12), default='PENDING', index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())

class CreativeRFQ(IdMixin, CreatedMixin, Base):
    __tablename__ = 'creative_rfqs'
    __table_args__ = (UniqueConstraint('buyer_id', 'listing_id', 'request_key', name='uq_creative_rfqs_request'),)
    listing_id: Mapped[int] = mapped_column(ForeignKey('creative_listings.id', ondelete='RESTRICT'), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    brief: Mapped[str] = mapped_column(Text)
    request_key: Mapped[str] = mapped_column(String(36))
    request_fingerprint: Mapped[str] = mapped_column(String(64))

class CreativeResponse(IdMixin, CreatedMixin, Base):
    __tablename__ = 'creative_responses'
    __table_args__ = (CheckConstraint("amount>0 AND currency='INR'", name='quote'), UniqueConstraint('rfq_id','request_key',name='uq_creative_responses_request'))
    rfq_id: Mapped[int] = mapped_column(ForeignKey('creative_rfqs.id', ondelete='RESTRICT'), index=True)
    terms: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    currency: Mapped[str] = mapped_column(String(3), default='INR')
    request_key: Mapped[str] = mapped_column(String(36))
    request_fingerprint: Mapped[str] = mapped_column(String(64))

class CreativeEngagement(IdMixin, TimestampMixin, Base):
    __tablename__ = 'creative_engagements'
    __table_args__ = (CheckConstraint("status IN ('ACCEPTED','DELIVERED','COMPLETED')", name='status'),)
    rfq_id: Mapped[int] = mapped_column(ForeignKey('creative_rfqs.id', ondelete='RESTRICT'), unique=True)
    response_id: Mapped[int] = mapped_column(ForeignKey('creative_responses.id', ondelete='RESTRICT'), unique=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey('creative_providers.id', ondelete='RESTRICT'), index=True)
    title: Mapped[str] = mapped_column(String(120))
    terms: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(12), default='ACCEPTED')
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class CreativeReview(IdMixin, CreatedMixin, Base):
    __tablename__ = 'creative_reviews'
    __table_args__ = (CheckConstraint('rating BETWEEN 1 AND 5', name='rating'),)
    engagement_id: Mapped[int] = mapped_column(ForeignKey('creative_engagements.id', ondelete='RESTRICT'), unique=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    rating: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
