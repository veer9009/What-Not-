from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_authentication import auth_client, register


def test_quota_commits_independently_and_has_bounded_attempts(db):
    from app.services.abuse import consume_quota, RateLimitExceeded
    engine = db.get_bind().engine
    scope = 'test:' + uuid4().hex
    consume_quota(engine, scope, 1, 3600)
    with pytest.raises(RateLimitExceeded):
        consume_quota(engine, scope, 1, 3600)


def test_concurrent_quota_does_not_admit_twice(migrated_engine):
    from app.services.abuse import consume_quota, RateLimitExceeded
    scope = 'test:' + uuid4().hex
    def request(_):
        try:
            consume_quota(migrated_engine, scope, 1, 3600)
            return 'allowed'
        except RateLimitExceeded:
            return 'limited'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(request, range(2))) == ['allowed', 'limited']


def test_beta_admission_rejects_uninvited_registration_without_echoing_email(auth_client):
    auth_client.app.state.settings.beta_allowed_emails = ['invited@example.com']
    response = register(auth_client)
    assert response.status_code == 403
    assert 'ravi' not in response.text.lower()


def test_login_failures_do_not_roll_back_abuse_count(auth_client):
    settings = auth_client.app.state.settings
    settings.environment = 'development'
    settings.auth_quarter_hour_limit = 1
    response = auth_client.post('/api/v1/auth/login', json={'email':'absent@example.com','password':'invalid'})
    assert response.status_code == 401
    response = auth_client.post('/api/v1/auth/login', json={'email':'absent@example.com','password':'invalid'})
    assert response.status_code == 429
    assert 'Retry-After' in response.headers
