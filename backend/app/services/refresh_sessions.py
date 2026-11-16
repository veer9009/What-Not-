"""Refresh rotation with user -> session -> token lock order.

Invalid rotations return None so replay revocation commits in the request's
outer transaction. Retain used digests for the entire session lifetime.
Expired families may be deleted by an explicitly scheduled maintenance job;
never delete history belonging to a session that can still authenticate.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets

from sqlalchemy import select

from app.models.auth_session import AuthRefreshToken, AuthSession
from app.repositories.users import UserRepository
from app.services.operations import write_operation


def token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def session_lifetime(role: str) -> timedelta:
    return timedelta(minutes=15) if role == 'ADMIN' else timedelta(hours=8)


class RefreshSessionService:
    def __init__(self, session):
        self.session = session

    def _locked_family(self, raw):
        if not isinstance(raw, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', raw):
            return None
        digest = token_digest(raw)
        # First locate without locks, then re-read under the common lock order.
        owner = self.session.execute(select(AuthSession.user_id, AuthSession.id)
            .join(AuthRefreshToken, AuthRefreshToken.session_id == AuthSession.id)
            .where(AuthRefreshToken.digest == digest)).first()
        if owner is None:
            return None
        user = UserRepository(self.session).get(owner.user_id, lock=True)
        family = self.session.scalar(select(AuthSession).where(AuthSession.id == owner.id)
            .with_for_update().execution_options(populate_existing=True))
        token = self.session.scalar(select(AuthRefreshToken).where(AuthRefreshToken.digest == digest)
            .with_for_update().execution_options(populate_existing=True))
        if user is None or family is None or token is None:
            return None
        return user, family, token

    def _issue(self, family, now):
        raw = secrets.token_urlsafe(32)
        self.session.add(AuthRefreshToken(digest=token_digest(raw), session_id=family.id, created_at=now))
        return raw

    @write_operation
    def create(self, user, previous_token=None):
        now = datetime.now(timezone.utc)
        if isinstance(previous_token, str) and re.fullmatch(r'[A-Za-z0-9_-]{43}', previous_token):
            previous = self.session.scalar(select(AuthSession)
                .join(AuthRefreshToken, AuthRefreshToken.session_id == AuthSession.id)
                .where(AuthRefreshToken.digest == token_digest(previous_token), AuthSession.user_id == user.id)
                .with_for_update(of=AuthSession).execution_options(populate_existing=True))
            if previous is not None:
                previous.revoked_at = previous.revoked_at or now
        family = AuthSession(id=secrets.token_hex(16), user_id=user.id, role=user.role,
            created_at=now, expires_at=now + session_lifetime(user.role))
        self.session.add(family)
        self.session.flush()
        return family, self._issue(family, now)

    @write_operation
    def rotate(self, raw):
        locked = self._locked_family(raw)
        if locked is None:
            return None
        user, family, token = locked
        now = datetime.now(timezone.utc)
        if token.used_at is not None or not user.is_active or user.role != family.role or family.expires_at <= now:
            family.revoked_at = family.revoked_at or now
            return None
        if family.revoked_at is not None:
            return None
        token.used_at = now
        return user, family, self._issue(family, now)

    @write_operation
    def revoke(self, raw):
        locked = self._locked_family(raw)
        if locked is not None:
            locked[1].revoked_at = locked[1].revoked_at or datetime.now(timezone.utc)

    def valid(self, session_id, user):
        family = self.session.get(AuthSession, session_id)
        return family is not None and family.user_id == user.id and family.revoked_at is None \
            and family.expires_at > datetime.now(timezone.utc) and family.role == user.role
