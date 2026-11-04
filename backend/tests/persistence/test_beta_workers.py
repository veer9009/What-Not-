from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from sqlalchemy import select
from app.models.events import EmailOutbox
from app.services.notifications import publish_event


def settings(**values):
    return SimpleNamespace(**(dict(outbox_batch_size=2, outbox_max_attempts=2,
        outbox_lease_seconds=120, outbox_backoff_seconds=1, email_provider='disabled') | values))


def test_lease_claim_retry_finite_attempt_and_stale_ack(db, records):
    from app.services.workers import claim_email_batch, acknowledge_email
    from app.services.mail import MailFailure
    publish_event(db, records['buyer'].id, 'lease:1', 'TEST', 'order', records['order'].id, 'Update', 'Body')
    config = settings()
    now = datetime.now(timezone.utc) + timedelta(seconds=1)
    claim = claim_email_batch(db, config, now=now)[0]
    db.flush()
    assert claim_email_batch(db, config, now=now) == []
    assert acknowledge_email(db, config, claim, failure=MailFailure('TIMEOUT'), now=now)
    db.flush()
    assert claim_email_batch(db, config, now=now) == []
    second = claim_email_batch(db, config, now=now+timedelta(seconds=3))[0]
    db.flush()
    assert not acknowledge_email(db, config, claim, reference='old')
    assert acknowledge_email(db, config, second, failure=MailFailure('TIMEOUT'))
    db.flush()
    row = db.scalar(select(EmailOutbox))
    assert row.state == 'FAILED' and row.attempts == 2
    assert claim_email_batch(db, config, now=now+timedelta(days=1)) == []


def test_disabled_provider_preserves_pending_without_claim(db, records):
    from app.services.workers import process_email
    publish_event(db, records['buyer'].id, 'disabled:1', 'TEST', 'order', records['order'].id, 'Update', 'Body')
    assert process_email(db.get_bind(), settings()) == 0
    row = db.scalar(select(EmailOutbox))
    assert row.state == 'PENDING' and row.attempts == 0


def test_expired_lease_recovers_with_new_token_and_preserved_attempt_budget(db, records):
    from app.services.workers import claim_email_batch, acknowledge_email
    publish_event(db, records['buyer'].id, 'restart:1', 'TEST', 'order', records['order'].id, 'Update', 'Body')
    config = settings()
    now = datetime.now(timezone.utc) + timedelta(seconds=1)
    old_claim = claim_email_batch(db, config, now=now)[0]
    db.flush()
    new_claim = claim_email_batch(db, config, now=now+timedelta(seconds=121))[0]
    db.flush()
    assert new_claim['token'] != old_claim['token']
    assert not acknowledge_email(db, config, old_claim, reference='stale-send')
    assert acknowledge_email(db, config, new_claim, reference='provider:stable')
    db.flush()
    row = db.scalar(select(EmailOutbox))
    assert row.state == 'SENT' and row.attempts == 2
    assert row.provider_reference == 'provider:stable'
