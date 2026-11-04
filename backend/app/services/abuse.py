"""Durable admission/abuse boundaries, separate from business rollback."""
from hashlib import sha256
import time

from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.abuse import RequestQuota


class RateLimitExceeded(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after


def consume_quota(engine, scope, limit, window_seconds, *, now=None):
    now = int(time.time() if now is None else now)
    window = now // window_seconds * window_seconds
    scope_hash = sha256(scope.encode('utf-8')).hexdigest()
    statement = insert(RequestQuota).values(scope_hash=scope_hash, window_start=window, attempts=1)
    statement = statement.on_conflict_do_update(
        index_elements=[RequestQuota.scope_hash, RequestQuota.window_start],
        set_={'attempts': RequestQuota.attempts + 1},
        where=RequestQuota.attempts < limit).returning(RequestQuota.attempts)
    # This connection has no user/business writes. A failed password or purchase
    # must not erase its quota count when the request's transaction rolls back.
    with Session(engine) as quota_session, quota_session.begin():
        allowed = quota_session.scalar(statement)
    if allowed is None:
        raise RateLimitExceeded(max(1, window + window_seconds - now))


def check_action_limit(session, settings, action, subject):
    if settings is None or not settings.abuse_limits_enabled or settings.environment == 'test':
        return
    limits = {'checkout': (settings.checkout_daily_limit, 86400),
              'address': (settings.address_daily_limit, 86400),
              'discovery': (settings.discovery_hourly_limit, 3600),
              'auth': (settings.auth_quarter_hour_limit, 900)}
    limit, window = limits[action]
    consume_quota(session.get_bind().engine, f'{action}:{subject}', limit, window)


def require_beta_admission(settings, email):
    if settings.beta_allowed_emails and email.lower() not in settings.beta_allowed_emails:
        raise HTTPException(403, 'This account is not admitted to the controlled beta')
