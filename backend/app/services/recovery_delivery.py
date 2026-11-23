"""Encrypted recovery outbox. Claims commit before bounded mail I/O.

Send locks are user -> recovery -> job. SMTP can accept before a lost DB ack:
retries are at least once, never exactly once. No provider exception is logged.
"""
import base64
from datetime import datetime, timedelta, timezone
import hmac
import json
import secrets
from uuid import uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.models.auth_recovery import PasswordRecovery
from app.models.recovery_delivery import RecoveryDelivery
from app.repositories.users import UserRepository
from app.services.mail import MailFailure, RecoverySMTPProvider


def aesgcm():
    # Lazy import: missing dependency must not break unrelated authentication.
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM


def seal(settings, plaintext, context):
    key_id = settings.recovery_active_key
    key = base64.b64decode(settings.recovery_encryption_keys[key_id].get_secret_value(), validate=True)
    nonce = secrets.token_bytes(12)
    return key_id, nonce + aesgcm()(key).encrypt(nonce, plaintext, context)


def unseal(settings, key_id, ciphertext, context):
    key = base64.b64decode(settings.recovery_encryption_keys[key_id].get_secret_value(), validate=True)
    return aesgcm()(key).decrypt(ciphertext[:12], ciphertext[12:], context)


def context(row):
    return f'whatnot-recovery:v1:{row.challenge}:{row.user_id}:{row.expires_at.astimezone(timezone.utc).isoformat()}'.encode()


def finish(row, state, code=None):
    row.state, row.last_error_code = state, code
    row.ciphertext = row.key_id = row.lease_token = row.lease_until = None


def cancel_recovery_jobs(session, user_id):
    session.execute(update(RecoveryDelivery).where(RecoveryDelivery.user_id == user_id,
        RecoveryDelivery.state.in_(['PENDING', 'LEASED'])).values(state='CANCELLED',
        ciphertext=None, key_id=None, lease_token=None, lease_until=None, last_error_code='SUPERSEDED'))


def enqueue_recovery(session, settings, row, email, otp):
    key_id, ciphertext = seal(settings, json.dumps({'email': email, 'otp': otp}).encode(), context(row))
    session.flush()  # Persist the challenge before the FK-dependent job.
    session.add(RecoveryDelivery(challenge=row.challenge, user_id=row.user_id,
        expires_at=row.expires_at, next_attempt_at=row.created_at,
        key_id=key_id, ciphertext=ciphertext))


def claim_recovery_batch(session, settings, *, now=None, limit=1):
    now = now or datetime.now(timezone.utc)
    rows = list(session.scalars(select(RecoveryDelivery).where(
        RecoveryDelivery.state.in_(['PENDING', 'LEASED']),
        or_(RecoveryDelivery.expires_at <= now,
            and_(RecoveryDelivery.state == 'PENDING', RecoveryDelivery.next_attempt_at <= now),
            and_(RecoveryDelivery.state == 'LEASED', RecoveryDelivery.lease_until <= now)))
        .order_by(RecoveryDelivery.next_attempt_at, RecoveryDelivery.challenge).limit(limit)
        .with_for_update(skip_locked=True).execution_options(populate_existing=True)))
    claims = []
    for row in rows:
        if row.expires_at <= now:
            finish(row, 'CANCELLED', 'EXPIRED')
        elif row.attempts >= settings.outbox_max_attempts:
            finish(row, 'FAILED', 'ATTEMPTS_EXHAUSTED')
        else:
            row.state, row.lease_token = 'LEASED', str(uuid4())
            row.attempts += 1
            row.lease_until = now + timedelta(seconds=settings.outbox_lease_seconds)
            claims.append({'challenge': row.challenge, 'user_id': row.user_id, 'token': row.lease_token})
    return claims


def send_recovery_claim(session, settings, claim, provider):
    # Claims carry identifiers only. Never decrypt before lock + validity checks.
    user = UserRepository(session).get(claim['user_id'], lock=True)
    recovery = session.scalar(select(PasswordRecovery).where(
        PasswordRecovery.challenge == claim['challenge']).with_for_update().execution_options(populate_existing=True))
    job = session.scalar(select(RecoveryDelivery).where(
        RecoveryDelivery.challenge == claim['challenge']).with_for_update().execution_options(populate_existing=True))
    now = datetime.now(timezone.utc)
    if job is None or job.state != 'LEASED' or job.lease_token != claim['token']:
        return False
    if job.lease_until <= now + timedelta(seconds=settings.recovery_smtp_deadline_seconds + 2):
        # Another worker may reclaim it; this stale worker must never send.
        # Reserve a full SMTP deadline before lease expiry, including when a
        # connection loss releases locks while the bounded child is still alive.
        return False
    if recovery is not None and min(job.expires_at, recovery.expires_at) <= now + timedelta(seconds=settings.recovery_smtp_deadline_seconds + 2):
        finish(job, 'CANCELLED', 'EXPIRED')
        return False
    from app.services.auth_recovery import digest
    if (user is None or recovery is None or recovery.user_id != user.id
            or not user.is_active or recovery.used_at or recovery.verified_at
            or recovery.attempts >= 5 or recovery.expires_at <= now or job.expires_at <= now
            or (settings.beta_allowed_emails and user.email.lower() not in settings.beta_allowed_emails)
            or not hmac.compare_digest(recovery.password_binding, digest(settings, 'password', user.password_hash))):
        finish(job, 'CANCELLED', 'CREDENTIAL_INVALID')
        return False
    try:
        payload = json.loads(unseal(settings, job.key_id, job.ciphertext, context(job)))
        if (payload['email'].lower() != user.email.lower()
                or not hmac.compare_digest(recovery.otp_digest,
                    digest(settings, 'otp', recovery.challenge + ':' + payload['otp']))):
            raise ValueError()
    except Exception:
        finish(job, 'FAILED', 'PAYLOAD_INVALID')
        return False
    try:
        provider.send(payload['email'], 'Your What Not verification code',
            f"Your verification code is {payload['otp']}. It expires 5 minutes after your request. "
            'If you did not request it, ignore this email.', 'password-recovery:' + job.challenge)
    except Exception as exc:
        # Never persist adapter text, arbitrary error codes or traceback data.
        permanent = isinstance(exc, MailFailure) and exc.permanent
        if permanent or job.attempts >= settings.outbox_max_attempts:
            finish(job, 'FAILED', 'DELIVERY_FAILED')
        else:
            job.state, job.last_error_code = 'PENDING', 'DELIVERY_RETRY'
            job.lease_token = job.lease_until = None
            job.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                seconds=settings.outbox_backoff_seconds * 2 ** (job.attempts - 1))
    else:
        finish(job, 'SENT')
    # A disconnected transaction must fail its ack; never manufacture success.
    session.flush()
    return True


def process_recovery_email(engine, settings, provider=None):
    if not settings.recovery_delivery_enabled:
        return 0
    from app.services.auth_recovery import recovery_ready
    recovery_ready(settings, provider)
    provider = provider or RecoverySMTPProvider(settings)
    processed = 0
    # Bounded batch and pool footprint: one connection per transaction, no
    # session advisory locks that could escape back into the connection pool.
    for _ in range(settings.outbox_batch_size):
        with Session(engine) as session, session.begin():
            claims = claim_recovery_batch(session, settings)
            # Expiry/exhaustion cleanup also consumes bounded batch work. It
            # must not stop this invocation before a fresh job behind it.
            made_progress = bool(session.dirty)
        if not claims:
            if made_progress:
                continue
            break
        with Session(engine) as session, session.begin():
            send_recovery_claim(session, settings, claims[0], provider)
        processed += 1
    return processed
