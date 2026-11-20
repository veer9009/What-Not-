"""Recovery security behavior against the designated disposable PostgreSQL schema."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import re
import secrets
from uuid import uuid4
from threading import Barrier

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.core.config import Settings
from app.core.security import hash_password, verify_password, InvalidCredentials
from app.main import create_app
from app.models import User
from app.models.auth_recovery import PasswordRecovery
from app.models.auth_session import AuthSession
from app.services.auth_recovery import PasswordRecoveryService, recovery_limit
from app.services.mail import FakeMailProvider
from app.schemas.auth import LoginRequest
from app.services.auth import AuthService
from app.services.refresh_sessions import RefreshSessionService

ORIGIN = 'https://testserver'
CSRF = {'Origin': ORIGIN, 'X-WhatNot-CSRF': '1'}
BASE = '/api/v1/auth/password-recovery/'


@pytest.fixture
def recovery(session_engine):
    config = Settings(_env_file=None, environment='test', jwt_secret_key=secrets.token_urlsafe(48),
                      password_recovery_key=secrets.token_urlsafe(48), abuse_limits_enabled=False,
                      cors_origins=[ORIGIN])
    app = create_app(config)
    mail = FakeMailProvider()
    app.state.recovery_mail_provider = mail
    def reader():
        with Session(session_engine) as session:
            yield session
    app.dependency_overrides[get_session] = reader
    email = uuid4().hex + '@example.com'
    with Session(session_engine) as session, session.begin():
        user = User(name='Synthetic recovery', email=email, phone=uuid4().hex,
                    password_hash=hash_password('old password'), role='BUYER')
        session.add(user)
        session.flush()
        uid = user.id
    with TestClient(app, base_url=ORIGIN) as client:
        yield client, session_engine, config, mail, uid, email


def requested(recovery):
    client, engine, config, mail, uid, email = recovery
    response = client.post(BASE + 'request', headers=CSRF, json={'email': email})
    assert response.status_code == 202
    challenge = response.json()['challenge']
    otp = re.search(r'\b[0-9]{6}\b', mail.messages['password-recovery:' + challenge][2]).group()
    return challenge, otp


def verified(recovery):
    challenge, otp = requested(recovery)
    response = recovery[0].post(BASE + 'verify', headers=CSRF, json={'challenge': challenge, 'otp': otp})
    assert response.status_code == 200
    return response.json()['reset_token']


def test_reset_revokes_all_sessions_preserves_password_and_is_single_use(recovery):
    client, engine, config, mail, uid, email = recovery
    login = client.post('/api/v1/auth/login', headers=CSRF, json={'email': email, 'password': 'old password'})
    assert login.status_code == 200
    first_refresh = client.cookies.get('wn_refresh')
    # A separate browser has no previous cookie, so both families remain active.
    client.cookies.clear()
    second_login = client.post('/api/v1/auth/login', headers=CSRF, json={'email': email, 'password': 'old password'})
    assert second_login.status_code == 200
    second_refresh = client.cookies.get('wn_refresh')
    with Session(engine) as session:
        families = session.scalars(select(AuthSession).where(AuthSession.user_id == uid)).all()
        assert len(families) == 2 and all(row.revoked_at is None for row in families)
    raw = verified(recovery)
    response = client.post(BASE + 'reset', headers=CSRF, json={'reset_token': raw, 'password': '  new password  '})
    assert response.status_code == 200
    assert 'Max-Age=0' in response.headers['set-cookie']
    for authentication, refresh_cookie in ((login, first_refresh), (second_login, second_refresh)):
        assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + authentication.json()['access_token']}).status_code == 401
        assert client.post('/api/v1/auth/refresh', headers={**CSRF, 'Cookie': 'wn_refresh=' + refresh_cookie}).status_code == 401
    assert client.post(BASE + 'reset', headers=CSRF, json={'reset_token': raw, 'password': 'another password'}).status_code == 400
    with Session(engine) as session:
        assert verify_password('  new password  ', session.get(User, uid).password_hash)
        assert not verify_password('new password', session.get(User, uid).password_hash)
        assert all(row.revoked_at for row in session.scalars(select(AuthSession).where(AuthSession.user_id == uid)))
        row = session.scalar(select(PasswordRecovery).where(PasswordRecovery.user_id == uid))
        assert raw != row.reset_digest and len(row.reset_digest) == 64


def test_wrong_attempts_are_committed_and_fifth_failure_blocks_correct_code(recovery):
    client, engine, *_ = recovery
    challenge, otp = requested(recovery)
    wrong = '000001' if otp == '000000' else '000000'
    for _ in range(5):
        assert client.post(BASE + 'verify', headers=CSRF, json={'challenge': challenge, 'otp': wrong}).status_code == 400
    assert client.post(BASE + 'verify', headers=CSRF, json={'challenge': challenge, 'otp': otp}).status_code == 400
    with Session(engine) as session:
        assert session.get(PasswordRecovery, challenge).attempts == 5


def test_expired_otp_and_reset_token_are_rejected(recovery):
    client, engine, *_ = recovery
    challenge, otp = requested(recovery)
    with Session(engine) as session, session.begin():
        row = session.get(PasswordRecovery, challenge)
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert client.post(BASE + 'verify', headers=CSRF, json={'challenge': challenge, 'otp': otp}).status_code == 400
    # Move cooldown outside its window without sleeping.
    with Session(engine) as session, session.begin():
        session.get(PasswordRecovery, challenge).created_at -= timedelta(seconds=61)
    raw = verified(recovery)
    with Session(engine) as session, session.begin():
        row = session.scalar(select(PasswordRecovery).where(PasswordRecovery.user_id == recovery[4], PasswordRecovery.reset_digest.is_not(None)))
        row.reset_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert client.post(BASE + 'reset', headers=CSRF, json={'reset_token': raw, 'password': 'new password'}).status_code == 400


def test_resend_cooldown_and_enumeration_have_same_http_shape(recovery):
    client, engine, config, mail, uid, email = recovery
    challenge, otp = requested(recovery)
    repeated = client.post(BASE + 'request', headers=CSRF, json={'email': email})
    absent = client.post(BASE + 'request', headers=CSRF, json={'email': uuid4().hex + '@example.com'})
    assert repeated.status_code == absent.status_code == 202
    assert repeated.json().keys() == absent.json().keys() == {'message', 'challenge', 'resend_after'}
    assert repeated.json()['message'] == absent.json()['message']
    assert repeated.json()['resend_after'] == absent.json()['resend_after'] == 60
    assert len(mail.messages) == 1
    with Session(engine) as session:
        assert otp not in repr(session.get(PasswordRecovery, challenge).__dict__)


def test_concurrent_reset_token_has_exactly_one_winner(recovery):
    raw = verified(recovery)
    client, engine, config, *_ = recovery
    def reset(_):
        with Session(engine) as session, session.begin():
            return PasswordRecoveryService(session, config).reset(raw, 'concurrent password')
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(reset, range(2))) == [False, True]


def test_quotas_survive_business_rollback_and_are_not_disabled_in_test(recovery):
    client, engine, config, mail, uid, email = recovery
    source = uuid4().hex
    for _ in range(5):
        with Session(engine) as session:
            with session.begin():
                assert recovery_limit(session, config, 'request', source, email)
                session.rollback()
    with Session(engine) as session, session.begin():
        assert not recovery_limit(session, config, 'request', source, email)


@pytest.mark.parametrize('state', ['inactive', 'not_admitted', 'delivery_failure'])
def test_ineligible_and_delivery_failure_keep_request_generic(recovery, state):
    client, engine, config, mail, uid, email = recovery
    if state == 'inactive':
        with Session(engine) as session, session.begin():
            session.get(User, uid).is_active = False
    elif state == 'not_admitted':
        config.beta_allowed_emails = ['somebodyelse@example.com']
    else:
        mail.failures = 1
    response = client.post(BASE + 'request', headers=CSRF, json={'email': email})
    assert response.status_code == 202
    assert response.json()['resend_after'] == 60
    assert not mail.messages
    assert response.headers['cache-control'] == 'no-store'


def test_password_change_invalidates_outstanding_reset(recovery):
    raw = verified(recovery)
    client, engine, config, mail, uid, email = recovery
    with Session(engine) as session, session.begin():
        session.get(User, uid).password_hash = hash_password('independently changed')
    assert client.post(BASE + 'reset', headers=CSRF, json={'reset_token': raw, 'password': 'new password'}).status_code == 400


def test_concurrent_verification_issues_only_one_reset_token(recovery):
    challenge, otp = requested(recovery)
    client, engine, config, *_ = recovery
    def verify(_):
        with Session(engine) as session, session.begin():
            return PasswordRecoveryService(session, config).verify(challenge, otp)
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sum(value is not None for value in executor.map(verify, range(2))) == 1


@pytest.mark.parametrize('already_verified', [False, True])
def test_new_challenge_supersedes_old_otp_and_reset_proof(recovery, already_verified):
    client, engine, config, mail, uid, email = recovery
    old_challenge, old_otp = requested(recovery)
    old_reset = None
    if already_verified:
        response = client.post(BASE + 'verify', headers=CSRF,
                               json={'challenge': old_challenge, 'otp': old_otp})
        assert response.status_code == 200
        old_reset = response.json()['reset_token']
    with Session(engine) as session, session.begin():
        session.get(PasswordRecovery, old_challenge).created_at -= timedelta(seconds=61)
    new_challenge, new_otp = requested(recovery)
    assert client.post(BASE + 'verify', headers=CSRF,
                       json={'challenge': old_challenge, 'otp': old_otp}).status_code == 400
    if old_reset:
        assert client.post(BASE + 'reset', headers=CSRF,
                           json={'reset_token': old_reset, 'password': 'rejected password'}).status_code == 400
    response = client.post(BASE + 'verify', headers=CSRF,
                           json={'challenge': new_challenge, 'otp': new_otp})
    assert response.status_code == 200
    assert client.post(BASE + 'reset', headers=CSRF,
                       json={'reset_token': response.json()['reset_token'], 'password': 'latest password'}).status_code == 200


def test_concurrent_resends_issue_one_code_and_cooldown_preserves_it(recovery):
    client, engine, config, mail, uid, email = recovery
    old_challenge, old_otp = requested(recovery)
    with Session(engine) as session, session.begin():
        session.get(PasswordRecovery, old_challenge).created_at -= timedelta(seconds=61)
    barrier = Barrier(2)

    def request_code(_):
        with Session(engine) as session, session.begin():
            barrier.wait(timeout=10)
            return PasswordRecoveryService(session, config).request(email)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(request_code, range(2)))
    deliveries = [delivery for _, delivery in results if delivery is not None]
    assert len(deliveries) == 1
    _, latest, otp = deliveries[0]
    with Session(engine) as session, session.begin():
        service = PasswordRecoveryService(session, config)
        assert service.verify(old_challenge, old_otp) is None
        suppressed, delivery = service.request(email)
        assert delivery is None
        assert service.verify(suppressed, otp) is None
        assert service.verify(latest, otp) is not None


@pytest.mark.parametrize('operation', ['login', 'refresh'])
def test_concurrent_reset_and_authentication_leave_no_old_password_session_active(recovery, operation):
    client, engine, config, mail, uid, email = recovery
    login = client.post('/api/v1/auth/login', headers=CSRF,
                        json={'email': email, 'password': 'old password'})
    assert login.status_code == 200
    old_refresh = client.cookies.get('wn_refresh')
    raw = verified(recovery)
    barrier = Barrier(2)

    def reset():
        with Session(engine) as session, session.begin():
            barrier.wait(timeout=10)
            return PasswordRecoveryService(session, config).reset(raw, 'password after race')

    def authenticate():
        try:
            with Session(engine) as session, session.begin():
                barrier.wait(timeout=10)
                if operation == 'login':
                    user = AuthService(session).login(LoginRequest(email=email, password='old password'))
                    family, credential = RefreshSessionService(session).create(user)
                    return credential
                rotated = RefreshSessionService(session).rotate(old_refresh)
                return rotated[2] if rotated else None
        except InvalidCredentials:
            # Reset committed before login obtained the user lock.
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        reset_result = executor.submit(reset)
        authentication_result = executor.submit(authenticate)
        assert reset_result.result(timeout=30) is True
        raced_refresh = authentication_result.result(timeout=30)

    with Session(engine) as session, session.begin():
        user = session.get(User, uid)
        assert verify_password('password after race', user.password_hash)
        families = session.scalars(select(AuthSession).where(AuthSession.user_id == uid)).all()
        assert families and all(family.revoked_at is not None for family in families)
        assert RefreshSessionService(session).rotate(old_refresh) is None
        if raced_refresh:
            assert RefreshSessionService(session).rotate(raced_refresh) is None
    assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + login.json()['access_token']}).status_code == 401
