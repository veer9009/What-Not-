"""Recovery credentials contain keyed digests only; no plaintext mail payload."""
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PasswordRecovery(Base):
    __tablename__ = 'password_recoveries'
    challenge: Mapped[str] = mapped_column(String(43), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), index=True)
    email_digest: Mapped[str] = mapped_column(String(64), index=True)
    otp_digest: Mapped[str] = mapped_column(String(64))
    password_binding: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reset_digest: Mapped[str | None] = mapped_column(String(64), unique=True)
    reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
