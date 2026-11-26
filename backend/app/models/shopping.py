"""Shopping persistence; no payment credentials or money movement."""
from sqlalchemy import BigInteger, ForeignKey, String, Boolean, Integer, JSON, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, CreatedMixin

class SellerPaymentSettings(TimestampMixin, Base):
    __tablename__='seller_payment_settings'
    __table_args__=(CheckConstraint("verification_status IN ('PENDING','APPROVED','REJECTED')",name='review_status'),CheckConstraint('revision >= 1',name='revision'))
    seller_id: Mapped[int]=mapped_column(BigInteger,ForeignKey('seller_profiles.id',ondelete='RESTRICT'),primary_key=True)
    upi_id: Mapped[str|None]=mapped_column(String(255))
    account_holder_name: Mapped[str|None]=mapped_column(String(120))
    accept_cod: Mapped[bool]=mapped_column(Boolean,default=True)
    accept_upi: Mapped[bool]=mapped_column(Boolean,default=False)
    verification_status: Mapped[str]=mapped_column(String(16),default='PENDING')
    revision: Mapped[int]=mapped_column(Integer,default=1)
    review_reason: Mapped[str|None]=mapped_column(String(1200))

class WishlistItem(CreatedMixin, Base):
    __tablename__='wishlist_items'
    buyer_id: Mapped[int]=mapped_column(BigInteger,ForeignKey('users.id',ondelete='RESTRICT'),primary_key=True)
    product_id: Mapped[int]=mapped_column(BigInteger,primary_key=True)

class CheckoutBatch(CreatedMixin, Base):
    __tablename__='checkout_batches'
    buyer_id: Mapped[int]=mapped_column(BigInteger,ForeignKey('users.id',ondelete='RESTRICT'),primary_key=True)
    key: Mapped[str]=mapped_column(String(36),primary_key=True)
    fingerprint: Mapped[str]=mapped_column(String(64))
    order_ids: Mapped[list]=mapped_column(JSON)
