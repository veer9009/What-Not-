"""Recovery-only encrypted delivery; never exposed through notification APIs."""
from datetime import datetime
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class RecoveryDelivery(Base):
    __tablename__ = 'recovery_deliveries'
    __table_args__ = (
        CheckConstraint("state IN ('PENDING','LEASED','SENT','FAILED','CANCELLED')", name='state'),
        CheckConstraint('attempts >= 0', name='attempts'),
        CheckConstraint("(state='LEASED' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) OR "
                        "(state<>'LEASED' AND lease_token IS NULL AND lease_until IS NULL)", name='lease'),
        CheckConstraint("(state IN ('SENT','FAILED','CANCELLED') AND ciphertext IS NULL AND key_id IS NULL) OR "
                        "(state IN ('PENDING','LEASED') AND ciphertext IS NOT NULL AND key_id IS NOT NULL)", name='payload'),
    )
    challenge: Mapped[str] = mapped_column(String(43), ForeignKey('password_recoveries.challenge', ondelete='RESTRICT'), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    key_id: Mapped[str | None] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(16), default='PENDING')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    last_error_code: Mapped[str | None] = mapped_column(String(40))
