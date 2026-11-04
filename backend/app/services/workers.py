"""Bounded outbox runner: lease commits precede network I/O."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import logging
from sqlalchemy import select, or_, and_, text
from sqlalchemy.orm import Session
from app.models.events import EmailOutbox
from app.models.user import User
from app.services.mail import SMTPMailProvider, MailFailure

logger = logging.getLogger(__name__)


def _send_guard(session, event_id, *, release=False):
    operation = 'pg_advisory_unlock' if release else 'pg_try_advisory_lock'
    return session.scalar(text(f'SELECT {operation}(hashtextextended(:key, 0))'),
        {'key': f'email-outbox-send:{event_id}'})


def claim_email_batch(session, settings, *, now=None, limit=None, send_guard=False):
    now = now or datetime.now(timezone.utc)
    rows = list(session.scalars(select(EmailOutbox).where(
        EmailOutbox.attempts < settings.outbox_max_attempts,
        or_(and_(EmailOutbox.state == 'PENDING', EmailOutbox.next_attempt_at <= now),
            and_(EmailOutbox.state == 'LEASED', EmailOutbox.lease_until <= now)))
        .order_by(EmailOutbox.id).limit(settings.outbox_batch_size if limit is None else limit)
        .with_for_update(skip_locked=True).execution_options(populate_existing=True)))
    claims = []
    for row in rows:
        if send_guard and not _send_guard(session, row.id):
            continue
        row.state = 'LEASED'
        row.attempts += 1
        row.lease_token = str(uuid4())
        row.lease_until = now + timedelta(seconds=settings.outbox_lease_seconds)
        recipient = session.get(User, row.recipient_id)
        claims.append(dict(id=row.id, token=row.lease_token, recipient=recipient.email if recipient else '',
            key=f'{row.event_key}:{row.recipient_id}', payload=row.payload))
    # Exhausted crash leases become observable failures rather than stuck leases.
    exhausted = list(session.scalars(select(EmailOutbox).where(EmailOutbox.state == 'LEASED',
        EmailOutbox.lease_until <= now, EmailOutbox.attempts >= settings.outbox_max_attempts)
        .limit(settings.outbox_batch_size if limit is None else limit).with_for_update(skip_locked=True)))
    for row in exhausted:
        if send_guard and not _send_guard(session, row.id):
            continue
        row.state = 'FAILED'
        row.last_error_code = 'ATTEMPTS_EXHAUSTED'
        row.lease_token = None
        row.lease_until = None
        if send_guard:
            _send_guard(session, row.id, release=True)
    return claims


def acknowledge_email(session, settings, claim, *, reference=None, failure=None, now=None):
    now = now or datetime.now(timezone.utc)
    row = session.scalar(select(EmailOutbox).where(EmailOutbox.id == claim['id'],
        EmailOutbox.state == 'LEASED', EmailOutbox.lease_token == claim['token']).with_for_update())
    if row is None:
        return False
    if failure is None:
        row.state = 'SENT'
        row.sent_at = now
        row.provider_reference = reference
        row.last_error_code = None
    else:
        row.state = 'FAILED' if failure.permanent or row.attempts >= settings.outbox_max_attempts else 'PENDING'
        row.last_error_code = failure.code
        row.next_attempt_at = now + timedelta(seconds=settings.outbox_backoff_seconds * 2 ** (row.attempts - 1))
    row.lease_token = None
    row.lease_until = None
    return True


def process_email(engine, settings, provider=None):
    if provider is None and settings.email_provider == 'disabled':
        return 0
    provider = provider or SMTPMailProvider(settings)
    processed = 0
    # This dedicated connection retains a session advisory guard across network
    # I/O, with no open transaction. An SMTP exchange may involve several socket
    # timeouts; expiry alone must never authorize a concurrent send of that event.
    with engine.connect() as connection:
        try:
            for _ in range(settings.outbox_batch_size):
                with Session(bind=connection) as session, session.begin():
                    claims = claim_email_batch(session, settings, limit=1, send_guard=True)
                if not claims:
                    break
                claim = claims[0]
                failure = None
                reference = None
                try:
                    reference = provider.send(claim['recipient'], claim['payload']['title'], claim['payload']['body'], claim['key'])
                except MailFailure as exc:
                    failure = exc
                except Exception:
                    failure = MailFailure('PROVIDER_FAILURE')
                with Session(bind=connection) as session, session.begin():
                    acknowledged = acknowledge_email(session, settings, claim, reference=reference, failure=failure)
                    _send_guard(session, claim['id'], release=True)
                processed += 1
                logger.info('email_outbox_result', extra={'event_id': claim['id'],
                    'error_code': failure.code if failure else None, 'acknowledged': acknowledged})
        finally:
            # Also clear any guard acquired before an unexpected claim/ack error.
            # Never return a session-locked connection to the pool.
            if connection.in_transaction():
                connection.rollback()
            connection.execute(text('SELECT pg_advisory_unlock_all()'))
            connection.commit()
    return processed
