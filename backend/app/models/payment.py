"""Direct-payment attestations; no funds, credentials or duplicated order totals."""
from datetime import datetime
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

PAYMENT_CHECKS = {
    'method': "method IN ('COD','UPI')",
    'status': "status IN ('PENDING','BUYER_REPORTED','SELLER_CONFIRMED')",
    'reference': "reference IS NULL OR (method='UPI' AND reference ~ '^[A-Za-z0-9][A-Za-z0-9 _./-]{0,99}$')",
    'reported_method': "method='UPI' OR reported_at IS NULL",
    'state_dates': "(status='PENDING' AND reported_at IS NULL AND confirmed_at IS NULL) OR "
                   "(status='BUYER_REPORTED' AND reported_at IS NOT NULL AND confirmed_at IS NULL) OR "
                   "(status='SELLER_CONFIRMED' AND confirmed_at IS NOT NULL)",
    'reference_report': 'reference IS NULL OR reported_at IS NOT NULL',
}


class OrderPayment(TimestampMixin, Base):
    __tablename__='order_payments'
    __table_args__=tuple(CheckConstraint(sql,name=name) for name,sql in PAYMENT_CHECKS.items())
    order_id: Mapped[int]=mapped_column(BigInteger,ForeignKey('orders.id',ondelete='RESTRICT'),primary_key=True)
    destination_upi_id: Mapped[str|None]=mapped_column(String(255))
    destination_name: Mapped[str|None]=mapped_column(String(120))
    destination_revision: Mapped[int|None]=mapped_column()
    method: Mapped[str]=mapped_column(String(3))
    status: Mapped[str]=mapped_column(String(24))
    reference: Mapped[str|None]=mapped_column(String(100))
    reported_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
