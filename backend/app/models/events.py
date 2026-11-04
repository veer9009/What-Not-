"""Durable transaction-local domain audit and recipient delivery records."""
from datetime import datetime
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, IdMixin, CreatedMixin


class AuditEvent(IdMixin, CreatedMixin, Base):
    __tablename__ = 'audit_events'
    actor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='RESTRICT'))
    actor_type: Mapped[str] = mapped_column(String(32), default='USER')
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(80))
    previous_status: Mapped[str | None] = mapped_column(String(40))
    next_status: Mapped[str | None] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(String(1200))


class Notification(IdMixin, CreatedMixin, Base):
    __tablename__ = 'notifications'
    __table_args__ = (UniqueConstraint('event_key', 'recipient_id', name='uq_notifications_event_recipient'),)
    recipient_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    event_key: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(1000))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailOutbox(IdMixin, CreatedMixin, Base):
    __tablename__ = 'email_outbox'
    __table_args__ = (UniqueConstraint('event_key', 'recipient_id', name='uq_email_outbox_event_recipient'),
        CheckConstraint("state IN ('PENDING','LEASED','SENT','FAILED')", name='state'),
        CheckConstraint('attempts >= 0', name='attempts'))
    recipient_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    event_key: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(16), server_default='PENDING')
    attempts: Mapped[int] = mapped_column(server_default='0')
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[str | None] = mapped_column(String(36))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_reference: Mapped[str | None] = mapped_column(String(200))
