"""In-memory ASGI proxy tests: no network listener, database, SMTP or Nginx changes."""
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.dependencies import get_transaction_session
from app.core.config import Settings
from app.main import create_app
from app.services.mail import FakeMailProvider


@pytest.fixture
def recovery_boundary(monkeypatch):
    config = Settings(_env_file=None, environment='test',
                      password_recovery_key='synthetic-proxy-key-' + 'x' * 40,
                      cors_origins=['https://testserver'])
    app = create_app(config)
    app.state.recovery_mail_provider = FakeMailProvider()
    session = SimpleNamespace(get_bind=lambda: SimpleNamespace(engine=object()))
    app.dependency_overrides[get_transaction_session] = lambda: session
    scopes = []
    monkeypatch.setattr('app.services.auth_recovery.consume_quota',
                        lambda engine, scope, limit, window_seconds: scopes.append(scope))

    class RecoveryStub:
        def __init__(self, session, settings):
            pass

        def request(self, email, *, allowed):
            assert allowed
            return 'synthetic-unpersisted-challenge', None

    monkeypatch.setattr('app.api.routes.auth.PasswordRecoveryService', RecoveryStub)
    return app, scopes


def request_code(app, peer, forwarded=None):
    headers = {'Origin': 'https://testserver', 'X-WhatNot-CSRF': '1',
               'X-Real-IP': '192.0.2.200', 'Forwarded': 'for=192.0.2.201'}
    if forwarded is not None:
        headers['X-Forwarded-For'] = forwarded
    with TestClient(app, base_url='https://testserver', client=peer) as client:
        response = client.post('/api/v1/auth/password-recovery/request',
                               headers=headers, json={'email': 'synthetic@example.com'})
    assert response.status_code == 202
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('spoofed', ['198.51.100.1', '198.51.100.2', '198.51.100.3, 127.0.0.1'])
def test_untrusted_peer_cannot_spoof_recovery_source(recovery_boundary, spoofed):
    app, scopes = recovery_boundary
    proxied = ProxyHeadersMiddleware(app, trusted_hosts='127.0.0.1')
    request_code(proxied, ('203.0.113.15', 43000), spoofed)
    assert scopes[0] == 'recovery:request:source:203.0.113.15'


def test_trusted_proxy_preserves_distinct_client_quota_buckets(recovery_boundary):
    app, scopes = recovery_boundary
    proxied = ProxyHeadersMiddleware(app, trusted_hosts='127.0.0.1')
    request_code(proxied, ('127.0.0.1', 43000), '198.51.100.10')
    request_code(proxied, ('127.0.0.1', 43001), '198.51.100.11')
    assert [scope for scope in scopes if ':source:' in scope] == [
        'recovery:request:source:198.51.100.10',
        'recovery:request:source:198.51.100.11',
    ]


def test_unknown_deployment_ignores_all_forwarding_headers(recovery_boundary):
    app, scopes = recovery_boundary
    request_code(app, ('203.0.113.16', 43000), '198.51.100.99')
    assert scopes[0] == 'recovery:request:source:203.0.113.16'


def test_trusted_proxy_without_forwarded_address_falls_back_to_peer(recovery_boundary):
    app, scopes = recovery_boundary
    request_code(ProxyHeadersMiddleware(app, trusted_hosts='127.0.0.1'), ('127.0.0.1', 43000))
    assert scopes[0] == 'recovery:request:source:127.0.0.1'
