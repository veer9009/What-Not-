"""User -> recovery -> delivery/session locking; durable encrypted live mail."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import re
import secrets

from fastapi import HTTPException
from sqlalchemy import select, update

from app.core.security import hash_password
from app.models.auth_recovery import PasswordRecovery
from app.models.auth_session import AuthSession
from app.repositories.users import UserRepository
from app.services.abuse import consume_quota, RateLimitExceeded
from app.services.mail import FakeMailProvider
from app.services.operations import write_operation

logger = logging.getLogger(__name__)
GENERIC_MESSAGE = 'If the account is eligible, a verification code will be sent.'
INVALID = 'Invalid or expired recovery credentials'


def recovery_key(settings):
    if settings.password_recovery_key is None:
        raise HTTPException(503, 'Password recovery is unavailable')
    return settings.password_recovery_key.get_secret_value().encode('utf-8')


def recovery_ready(settings, provider=None):
    """Default-off activation; legacy fake-only tests cannot enable live SMTP."""
    recovery_key(settings)
    synthetic = settings.environment == 'test' and isinstance(provider, FakeMailProvider)
    if not settings.recovery_delivery_enabled:
        if synthetic:
            return
        raise HTTPException(503, 'Password recovery is unavailable')
    if not settings.recovery_active_key or not settings.recovery_encryption_keys or (settings.email_provider != 'smtp' and not synthetic):
        raise HTTPException(503, 'Password recovery is unavailable')
    try:
        from app.services.recovery_delivery import aesgcm
        aesgcm()
    except ImportError:
        raise HTTPException(503, 'Password recovery is unavailable') from None


def digest(settings, purpose, raw):
    return hmac.new(recovery_key(settings), (purpose + ':' + raw).encode('utf-8'), hashlib.sha256).hexdigest()


def recovery_limit(session, settings, action, source, email=None):
    """Always enforced, including test mode and when other abuse controls are off."""
    engine = session.get_bind().engine
    try:
        consume_quota(engine, 'recovery:' + action + ':source:' + source, 30, 900)
        if email is not None:
            consume_quota(engine, 'recovery:request:email:' + digest(settings, 'email', email), 5, 900)
    except RateLimitExceeded:
        return False
    return True


def deliver_recovery(settings, delivery, provider=None):
    if delivery is None:
        return
    # Never enable transient SMTP delivery with a flag: a durable design is required.
    if settings.environment != 'test' or not isinstance(provider, FakeMailProvider):
        logger.info('password_recovery_delivery_disabled')
        return
    email, challenge, otp = delivery
    try:
        provider.send(email, 'Your What Not verification code',
                      f'Your verification code is {otp}. It expires in 5 minutes. If you did not request it, ignore this email.',
                      'password-recovery:' + challenge)
    except Exception:
        # Adapter errors must never serialize recipients, credentials or message bodies.
        logger.warning('password_recovery_delivery_failed')


class PasswordRecoveryService:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    def _binding(self, user):
        return digest(self.settings, 'password', user.password_hash)

    def _eligible(self, user):
        return user is not None and user.is_active and (not self.settings.beta_allowed_emails
            or user.email.lower() in self.settings.beta_allowed_emails)

    @write_operation
    def request(self, email, *, allowed=True):
        now = datetime.now(timezone.utc)
        challenge, otp = secrets.token_urlsafe(32), f'{secrets.randbelow(1000000):06d}'
        if not allowed:
            return challenge, None
        email_digest = digest(self.settings, 'email', email)
        matches = UserRepository(self.session).by_normalized_email(email)
        user = UserRepository(self.session).get(matches[0].id, lock=True) if len(matches) == 1 else None
        now = datetime.now(timezone.utc)
        recent = self.session.scalar(select(PasswordRecovery.challenge).where(
            PasswordRecovery.email_digest == email_digest,
            PasswordRecovery.created_at > now - timedelta(seconds=60)).limit(1))
        eligible = self._eligible(user) and allowed and recent is None
        if eligible:
            # The user lock serializes issuance, verification and reset. Retire all
            # older credentials, including already verified reset proofs, before
            # issuing a replacement. Suppressed requests leave the current code valid.
            self.session.execute(update(PasswordRecovery).where(
                PasswordRecovery.user_id == user.id,
                PasswordRecovery.used_at.is_(None)).values(used_at=now))
            if self.settings.recovery_delivery_enabled:
                from app.services.recovery_delivery import cancel_recovery_jobs
                cancel_recovery_jobs(self.session, user.id)
        # Every attempt receives a fresh opaque challenge, including suppressed mail.
        row = PasswordRecovery(challenge=challenge, user_id=user.id if eligible else None,
            email_digest=email_digest, otp_digest=digest(self.settings, 'otp', challenge + ':' + otp),
            password_binding=self._binding(user) if eligible else digest(self.settings, 'password', challenge),
            created_at=now, expires_at=now + timedelta(minutes=5), attempts=0)
        self.session.add(row)
        if eligible and self.settings.recovery_delivery_enabled:
            from app.services.recovery_delivery import enqueue_recovery
            enqueue_recovery(self.session, self.settings, row, email, otp)
            logger.info('password_recovery_requested')
            return challenge, None
        logger.info('password_recovery_requested')
        return challenge, (email, challenge, otp) if eligible else None

    def _locked(self, *, challenge=None, reset_token=None):
        query = select(PasswordRecovery).where(PasswordRecovery.challenge == challenge) if challenge is not None else \
            select(PasswordRecovery).where(PasswordRecovery.reset_digest == digest(self.settings, 'reset', reset_token))
        row = self.session.scalar(query)
        if row is None:
            return None, None
        user = UserRepository(self.session).get(row.user_id, lock=True) if row.user_id is not None else None
        row = self.session.scalar(query.with_for_update().execution_options(populate_existing=True))
        return row, user

    @write_operation
    def verify(self, challenge, otp):
        row, user = self._locked(challenge=challenge)
        now = datetime.now(timezone.utc)
        if row is None or row.used_at or row.verified_at or row.expires_at <= now or row.attempts >= 5:
            return None
        row.attempts += 1
        valid = hmac.compare_digest(row.otp_digest, digest(self.settings, 'otp', challenge + ':' + otp))
        if not valid or not re.fullmatch(r'[0-9]{6}', otp) or not self._eligible(user) or not hmac.compare_digest(row.password_binding, self._binding(user)):
            logger.info('password_recovery_verification_denied')
            return None
        raw = secrets.token_urlsafe(32)
        row.verified_at, row.reset_digest = now, digest(self.settings, 'reset', raw)
        row.reset_expires_at = now + timedelta(minutes=5)
        if self.settings.recovery_delivery_enabled:
            from app.services.recovery_delivery import cancel_recovery_jobs
            cancel_recovery_jobs(self.session, user.id)
        return raw

    @write_operation
    def reset(self, reset_token, password):
        row, user = self._locked(reset_token=reset_token)
        now = datetime.now(timezone.utc)
        if row is None or row.used_at or row.reset_expires_at is None or row.reset_expires_at <= now \
                or not self._eligible(user) or not hmac.compare_digest(row.password_binding, self._binding(user)):
            return False
        user.password_hash = hash_password(password)
        row.used_at = now
        if self.settings.recovery_delivery_enabled:
            from app.services.recovery_delivery import cancel_recovery_jobs
            cancel_recovery_jobs(self.session, user.id)
        families = self.session.scalars(select(AuthSession).where(AuthSession.user_id == user.id)
            .order_by(AuthSession.id).with_for_update()).all()
        for family in families:
            family.revoked_at = family.revoked_at or now
        logger.info('password_recovery_reset_completed')
        return True
