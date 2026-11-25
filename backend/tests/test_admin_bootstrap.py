from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.bootstrap_admin import validate_target, validate_identity


def settings(database='whatnot_pilot', environment='production'):
    return SimpleNamespace(environment=environment,
        database_url=SimpleNamespace(get_secret_value=lambda: 'postgresql+psycopg://whatnot_runtime@127.0.0.1/' + database),
        beta_allowed_emails=[f'pilot{n}@example.com' for n in range(10)])


def test_bootstrap_target_refuses_original_wrong_target_or_nonproduction_before_connection():
    for configured, expected, environment in [
        ('whatnot_app_dev', 'whatnot_app_dev', 'production'),
        ('whatnot_pilot', 'whatnot_pilot_other', 'production'),
        ('whatnot_pilot', 'whatnot_pilot', 'development'),
    ]:
        with pytest.raises(RuntimeError):
            validate_target(settings(configured, environment), expected)


@pytest.mark.parametrize('count',[0,1,5,9,11])
def test_bootstrap_requires_exactly_ten_selected_accounts(count):
    config = settings()
    config.beta_allowed_emails = [f'pilot{n}@example.com' for n in range(count)]
    with pytest.raises(RuntimeError):
        validate_target(config, 'whatnot_pilot')
    validate_target(settings(), 'whatnot_pilot')


@pytest.mark.parametrize('actual', [
    ('whatnot_app_dev', 'whatnot_runtime', '127.0.0.1', 5432, 123),
    ('whatnot_pilot', 'postgres', '127.0.0.1', 5432, 123),
    ('whatnot_pilot', 'whatnot_runtime', '127.0.0.2', 5432, 123),
    ('whatnot_pilot', 'whatnot_runtime', '127.0.0.1', 5433, 123),
    ('whatnot_pilot', 'whatnot_runtime', '127.0.0.1', 5432, 124),
])
def test_bootstrap_identity_mismatch_refuses(actual):
    with pytest.raises(RuntimeError):
        validate_identity(actual, 'whatnot_pilot', '127.0.0.1', 5432, 123)


def test_bootstrap_identity_exact_match():
    validate_identity(('whatnot_pilot', 'whatnot_runtime', '127.0.0.1', 5432, 123),
                      'whatnot_pilot', '127.0.0.1', 5432, 123)


def test_existing_users_or_schema_mismatch_refuses_without_hashing_or_insert(monkeypatch):
    from app.bootstrap_admin import create_initial_admin
    from app.schemas.auth import UserRegistration
    details = UserRegistration(name='Unit Operator', email='pilot0@example.com', phone='synthetic',
                               password='synthetic-only-password')
    hasher = Mock()
    monkeypatch.setattr('app.bootstrap_admin.hash_password', hasher)
    for values in [['0007'], ['0008'], ['0009', 1]]:
        session = Mock()
        session.execute.return_value.one.return_value = ('whatnot_pilot', 'whatnot_runtime', '127.0.0.1', 5432, 123)
        session.scalar.side_effect = values
        with pytest.raises(RuntimeError):
            create_initial_admin(session, settings(), 'whatnot_pilot', '127.0.0.1', 5432, 123, details)
        hasher.assert_not_called()


def test_successful_bootstrap_uses_existing_service_with_argon2_admin_input(monkeypatch):
    from app.bootstrap_admin import create_initial_admin
    from app.core.security import verify_password
    from app.schemas.auth import UserRegistration
    session = Mock()
    session.execute.return_value.one.return_value = ('whatnot_pilot', 'whatnot_runtime', '127.0.0.1', 5432, 123)
    session.scalar.side_effect = ['0013', 0]
    service = Mock()
    monkeypatch.setattr('app.bootstrap_admin.UserService', lambda bound: service)
    details = UserRegistration(name='Unit Operator', email='pilot0@example.com', phone='synthetic',
                               password='synthetic-only-password')
    create_initial_admin(session, settings(), 'whatnot_pilot', '127.0.0.1', 5432, 123, details)
    created = service.create.call_args.args[0]
    assert created.role.value == 'ADMIN'
    assert verify_password('synthetic-only-password', created.password_hash.get_secret_value())


def test_unadmitted_admin_is_rejected_before_database_or_password_work(monkeypatch):
    from app.bootstrap_admin import create_initial_admin
    from app.schemas.auth import UserRegistration
    session = Mock()
    details = UserRegistration(name='Unit Operator', email='outsider@example.com', phone='synthetic',
                               password='synthetic-only-password')
    hasher = Mock()
    monkeypatch.setattr('app.bootstrap_admin.hash_password', hasher)
    with pytest.raises(RuntimeError):
        create_initial_admin(session, settings(), 'whatnot_pilot', '127.0.0.1', 5432, 123, details)
    session.execute.assert_not_called()
    hasher.assert_not_called()
