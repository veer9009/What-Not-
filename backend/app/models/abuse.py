"""Pseudonymous fixed-window counters; no raw IP/email/location is stored."""
from sqlalchemy import BigInteger, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class RequestQuota(Base):
    __tablename__ = 'request_quotas'
    __table_args__ = (CheckConstraint('attempts > 0', name='attempts'),)
    scope_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    attempts: Mapped[int] = mapped_column(nullable=False)
