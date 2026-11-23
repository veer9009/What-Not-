"""Real AEAD + PostgreSQL, guarded test schema only; fake SMTP exclusively."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from threading import Barrier, Event

import pytest
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.auth_recovery import PasswordRecovery
from app.models.recovery_delivery import RecoveryDelivery
from app.models.events import EmailOutbox, Notification
from app.services.auth_recovery import PasswordRecoveryService
from app.services.mail import FakeMailProvider, MailFailure
from app.services.recovery_delivery import (claim_recovery_batch, context, process_recovery_email,
                                          send_recovery_claim, unseal)
from .test_password_recovery import recovery, BASE, CSRF


@pytest.fixture
def durable(recovery):
    pytest.importorskip('cryptography', reason='Real AEAD dependency required')
    settings = recovery[2]
    settings.recovery_encryption_keys = {'v1': SecretStr(base64.b64encode(b'synthetic-encryption-key-32bytes!'.ljust(32, b'x')[:32]).decode())}
    settings.recovery_active_key = 'v1'
    settings.recovery_delivery_enabled = True
    settings.outbox_batch_size = 4
    yield recovery
    from app.services.recovery_delivery import cancel_recovery_jobs
    with Session(recovery[1]) as session, session.begin():
        cancel_recovery_jobs(session, recovery[4])


def request(durable):
    client, engine, settings, mail, uid, email = durable
    response = client.post(BASE + 'request', headers=CSRF, json={'email': email})
    assert response.status_code == 202
    return response.json()['challenge']


def job(engine, challenge):
    with Session(engine) as session:
        return session.get(RecoveryDelivery, challenge)


def claim(engine, settings):
    with Session(engine) as session, session.begin():
        return claim_recovery_batch(session, settings)[0]


def test_api_persists_encrypted_job_without_background_mail_and_worker_erases(durable):
    client, engine, settings, mail, uid, email = durable
    challenge = request(durable)
    assert not mail.messages
    with Session(engine) as session:
        row = session.get(RecoveryDelivery, challenge)
        payload = json.loads(unseal(settings, row.key_id, row.ciphertext, context(row)))
        assert payload['email'] == email and len(payload['otp']) == 6
        assert payload['otp'].encode() not in row.ciphertext
        assert not session.scalars(select(EmailOutbox).where(EmailOutbox.recipient_id == uid)).all()
        assert not session.scalars(select(Notification).where(Notification.recipient_id == uid)).all()
    assert process_recovery_email(engine, settings, mail) == 1
    row = job(engine, challenge)
    assert row.state == 'SENT' and row.ciphertext is None and row.key_id is None
    assert len(mail.messages) == 1


def test_suppression_ineligible_and_supersession_erase_only_replaced_job(durable):
    client, engine, settings, mail, uid, email = durable
    first = request(durable)
    suppressed = request(durable)
    assert job(engine, suppressed) is None and job(engine, first).state == 'PENDING'
    with Session(engine) as session, session.begin():
        session.get(PasswordRecovery, first).created_at -= timedelta(seconds=61)
        session.get(PasswordRecovery, suppressed).created_at -= timedelta(seconds=61)
    newest = request(durable)
    assert job(engine, first).state == 'CANCELLED' and job(engine, first).ciphertext is None
    assert job(engine, newest).state == 'PENDING'
    response = client.post(BASE + 'request', headers=CSRF, json={'email': 'absent@example.com'})
    assert response.status_code == 202 and job(engine, response.json()['challenge']) is None


def test_enqueue_failure_rolls_back_supersession_and_new_challenge(durable, monkeypatch):
    _, engine, settings, _, uid, email = durable
    first = request(durable)
    with Session(engine) as session, session.begin():
        session.get(PasswordRecovery, first).created_at -= timedelta(seconds=61)
    def fail(*args):
        raise RuntimeError('synthetic enqueue failure')
    monkeypatch.setattr('app.services.recovery_delivery.enqueue_recovery', fail)
    with Session(engine) as session, session.begin():
        with pytest.raises(RuntimeError):
            PasswordRecoveryService(session, settings).request(email)
    assert job(engine, first).state == 'PENDING'
    with Session(engine) as session:
        rows = list(session.scalars(select(PasswordRecovery).where(PasswordRecovery.user_id == uid)))
        assert len(rows) == 1 and rows[0].used_at is None


@pytest.mark.parametrize('reason', ['expired', 'password_changed', 'verified', 'inactive', 'tampered', 'missing_key'])
def test_invalid_work_is_never_sent_and_payload_is_erased(durable, reason):
    from app.models import User
    _, engine, settings, mail, uid, _ = durable
    challenge = request(durable)
    with Session(engine) as session, session.begin():
        row = session.get(PasswordRecovery, challenge)
        delivery = session.get(RecoveryDelivery, challenge)
        if reason == 'expired':
            row.expires_at = delivery.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(hours=1)
        elif reason == 'password_changed':
            session.get(User, uid).password_hash = 'changed password binding'
        elif reason == 'verified':
            row.verified_at = datetime.now(timezone.utc)
        elif reason == 'inactive':
            session.get(User, uid).is_active = False
        elif reason == 'tampered':
            delivery.ciphertext = delivery.ciphertext[:-1] + bytes([delivery.ciphertext[-1] ^ 1])
        else:
            delivery.key_id = 'retired-key'
    process_recovery_email(engine, settings, mail)
    row = job(engine, challenge)
    assert row.state in ('CANCELLED', 'FAILED') and row.ciphertext is None and not mail.messages


def test_restart_reclaims_expired_lease_and_old_token_cannot_send(durable):
    _, engine, settings, mail, *_ = durable
    challenge = request(durable)
    old = claim(engine, settings)
    with Session(engine) as session, session.begin():
        session.get(RecoveryDelivery, challenge).lease_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    newest = claim(engine, settings)
    assert old['token'] != newest['token']
    with Session(engine) as session, session.begin():
        assert not send_recovery_claim(session, settings, old, mail)
    with Session(engine) as session, session.begin():
        assert send_recovery_claim(session, settings, newest, mail)
    assert job(engine, challenge).attempts == 2 and len(mail.messages) == 1


def test_worker_reserves_entire_smtp_deadline_before_lease_expiry(durable):
    _, engine, settings, mail, *_ = durable
    challenge = request(durable)
    leased = claim(engine, settings)
    with Session(engine) as session, session.begin():
        session.get(RecoveryDelivery, challenge).lease_until = datetime.now(timezone.utc) + timedelta(seconds=1)
    with Session(engine) as session, session.begin():
        assert not send_recovery_claim(session, settings, leased, mail)
    assert not mail.messages and job(engine, challenge).state == 'LEASED'


def test_worker_does_not_start_mail_when_otp_will_expire_inside_deadline(durable):
    from app.services.recovery_delivery import seal
    _, engine, settings, mail, *_ = durable
    challenge = request(durable)
    leased = claim(engine, settings)
    with Session(engine) as session, session.begin():
        delivery = session.get(RecoveryDelivery, challenge)
        payload = unseal(settings, delivery.key_id, delivery.ciphertext, context(delivery))
        expiry = datetime.now(timezone.utc) + timedelta(seconds=1)
        delivery.expires_at = session.get(PasswordRecovery, challenge).expires_at = expiry
        delivery.key_id, delivery.ciphertext = seal(settings, payload, context(delivery))
    with Session(engine) as session, session.begin():
        assert not send_recovery_claim(session, settings, leased, mail)
    assert not mail.messages and job(engine, challenge).state == 'CANCELLED'


@pytest.mark.parametrize('permanent', [False, True])
def test_failures_are_bounded_backed_off_sanitized_and_erased(durable, permanent, caplog):
    _, engine, settings, _, *_ = durable
    challenge = request(durable)
    settings.outbox_max_attempts = 2
    class Failure(FakeMailProvider):
        def send(self, *args):
            raise MailFailure('SENSITIVE-ADAPTER-TEXT', permanent=permanent)
    assert process_recovery_email(engine, settings, Failure()) == 1
    row = job(engine, challenge)
    if not permanent:
        assert row.state == 'PENDING' and row.ciphertext
        assert row.next_attempt_at > datetime.now(timezone.utc) + timedelta(seconds=50)
        with Session(engine) as session, session.begin():
            session.get(RecoveryDelivery, challenge).next_attempt_at -= timedelta(seconds=120)
        process_recovery_email(engine, settings, Failure())
    row = job(engine, challenge)
    assert row.state == 'FAILED' and row.ciphertext is None
    assert row.last_error_code == 'DELIVERY_FAILED'
    assert 'SENSITIVE-ADAPTER-TEXT' not in caplog.text


def test_exhausted_crash_lease_is_erased(durable):
    _, engine, settings, mail, *_ = durable
    challenge = request(durable)
    claim(engine, settings)
    with Session(engine) as session, session.begin():
        row = session.get(RecoveryDelivery, challenge)
        row.attempts = settings.outbox_max_attempts
        row.lease_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    process_recovery_email(engine, settings, mail)
    row = job(engine, challenge)
    assert row.state == 'FAILED' and row.ciphertext is None and not mail.messages


def test_expiry_cleanup_does_not_stop_batch_before_fresh_mail(durable):
    import secrets
    from app.services.recovery_delivery import seal
    _, engine, settings, mail, uid, email = durable
    newest = request(durable)
    now = datetime.now(timezone.utc)
    with Session(engine) as session, session.begin():
        binding = session.get(PasswordRecovery, newest).password_binding
        for _ in range(2):
            challenge = secrets.token_urlsafe(32)
            expired = now - timedelta(seconds=1)
            row = PasswordRecovery(challenge=challenge, user_id=uid, email_digest='e' * 64,
                otp_digest='d' * 64, password_binding=binding, created_at=now-timedelta(minutes=6),
                expires_at=expired, attempts=0)
            session.add(row);session.flush()
            key_id, ciphertext = seal(settings, json.dumps({'email':email,'otp':'123456'}).encode(), context(row))
            session.add(RecoveryDelivery(challenge=challenge,user_id=uid,key_id=key_id,ciphertext=ciphertext,
                expires_at=expired,next_attempt_at=now-timedelta(minutes=6)))
    assert process_recovery_email(engine, settings, mail) == 1
    assert job(engine, newest).state == 'SENT' and len(mail.messages) == 1


def test_concurrent_claims_have_exactly_one_owner(durable):
    _, engine, settings, *_ = durable
    request(durable)
    barrier = Barrier(2)
    def run(_):
        with Session(engine) as session, session.begin():
            barrier.wait(timeout=10)
            return claim_recovery_batch(session, settings)
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sum(len(rows) for rows in executor.map(run, range(2))) == 1


def test_active_send_blocks_supersession_and_competing_worker(durable):
    _, engine, settings, _, uid, email = durable
    challenge = request(durable)
    with Session(engine) as session, session.begin():
        session.get(PasswordRecovery, challenge).created_at -= timedelta(seconds=61)
    started, release = Event(), Event()
    class Slow(FakeMailProvider):
        def send(self, *args):
            started.set()
            assert release.wait(timeout=4)
            return super().send(*args)
    mail = Slow()
    def request_new():
        with Session(engine) as session, session.begin():
            return PasswordRecoveryService(session, settings).request(email)
    with ThreadPoolExecutor(max_workers=2) as executor:
        sending = executor.submit(process_recovery_email, engine, settings, mail)
        assert started.wait(timeout=10)
        try:
            replacement = executor.submit(request_new)
            with Session(engine) as session, session.begin():
                assert not claim_recovery_batch(session, settings, now=datetime.now(timezone.utc) + timedelta(seconds=121))
            assert not replacement.done()
        finally:
            release.set()
        sending.result(timeout=15)
        new_challenge, delivery = replacement.result(timeout=15)
    assert delivery is None and new_challenge != challenge
    with Session(engine) as session:
        assert session.get(PasswordRecovery, challenge).used_at is not None


def test_database_connection_loss_during_active_send_never_acks_and_can_retry(durable):
    _, engine, settings, _, *_ = durable
    challenge = request(durable)
    leased = claim(engine, settings)
    session = Session(engine)
    class Disconnect(FakeMailProvider):
        def send(self, *args):
            super().send(*args)  # SMTP accepted before the DB connection was lost.
            session.connection().connection.driver_connection.close()
            return 'synthetic-accepted'
    mail = Disconnect()
    try:
        with pytest.raises(SQLAlchemyError):
            with session.begin():
                send_recovery_claim(session, settings, leased, mail)
    finally:
        session.close()
    assert len(mail.messages) == 1
    assert job(engine, challenge).state == 'LEASED'
    with Session(engine) as session, session.begin():
        session.get(RecoveryDelivery, challenge).lease_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    retry = FakeMailProvider()
    process_recovery_email(engine, settings, retry)
    assert len(retry.messages) == 1 and job(engine, challenge).state == 'SENT'
    assert set(retry.messages) == set(mail.messages)  # stable ID, duplicate acceptance is possible
