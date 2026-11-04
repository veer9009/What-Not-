"""Enqueue safely inside the caller's transaction; never send mail here."""
from datetime import datetime, timezone
from sqlalchemy import select, func, update
from sqlalchemy.dialects.postgresql import insert
from app.models.events import Notification, EmailOutbox
from app.services.users import require_user, pagination
from app.services.errors import OwnershipError
from app.services.operations import write_operation


def publish_event(session, recipient_id, event_key, kind, entity_type, entity_id, title, body):
    values = dict(recipient_id=recipient_id, event_key=event_key, kind=kind,
                  entity_type=entity_type, entity_id=entity_id, title=title, body=body)
    session.execute(insert(Notification).values(**values).on_conflict_do_nothing(
        constraint='uq_notifications_event_recipient'))
    session.execute(insert(EmailOutbox).values(recipient_id=recipient_id, event_key=event_key,
        kind=kind, payload=dict(title=title, body=body)).on_conflict_do_nothing(
        constraint='uq_email_outbox_event_recipient'))


class NotificationService:
    def __init__(self, session):
        self.session = session

    def list(self, actor_id, *, offset=0, limit=50):
        require_user(self.session, actor_id)
        offset, limit = pagination(offset, limit)
        return list(self.session.scalars(select(Notification).where(Notification.recipient_id == actor_id)
            .order_by(Notification.id.desc()).offset(offset).limit(limit)))

    def unread_count(self, actor_id):
        require_user(self.session, actor_id)
        return self.session.scalar(select(func.count()).select_from(Notification).where(
            Notification.recipient_id == actor_id, Notification.read_at.is_(None)))

    @write_operation
    def read_one(self, actor_id, notification_id):
        require_user(self.session, actor_id)
        row = self.session.scalar(select(Notification).where(Notification.id == notification_id,
            Notification.recipient_id == actor_id).with_for_update())
        if row is None:
            raise OwnershipError('Notification is unavailable')
        if row.read_at is None:
            row.read_at = datetime.now(timezone.utc)
        return row

    @write_operation
    def read_all(self, actor_id):
        require_user(self.session, actor_id)
        return self.session.execute(update(Notification).where(Notification.recipient_id == actor_id,
            Notification.read_at.is_(None)).values(read_at=datetime.now(timezone.utc))).rowcount
