"""Reject wrong administrative contexts and premature maintenance release."""
import importlib.util
from pathlib import Path
import pytest


def module():
    path=Path(__file__).resolve().parents[2]/'docs/security/cutover_control.py'
    assert path.exists(), 'Separate maintenance-context guard is required'
    spec=importlib.util.spec_from_file_location('cutover_control_test',path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize('identity',[
    ('whatnot_app_dev','127.0.0.1/32',5432,41069,True),
    ('postgres','127.0.0.1/32',5433,41069,True),
    ('postgres','192.0.2.1/32',5432,41069,True),
    ('postgres','127.0.0.1/32',5432,99,True),
    ('postgres','127.0.0.1/32',5432,41069,False),
])
def test_wrong_context_cannot_change_target_connection_permissions(identity):
    with pytest.raises(RuntimeError):
        module().verify_control_identity(identity,41069)


def test_postgres_control_context_is_allowed():
    module().verify_control_identity(('postgres','127.0.0.1/32',5432,41069,True),41069)


@pytest.mark.parametrize('settings',[[],[(['default_transaction_read_only=on'],)]])
def test_fresh_or_retained_known_maintenance_state_can_resume(settings):
    module().verify_defaults(settings)


def test_unknown_database_defaults_fail_closed():
    with pytest.raises(RuntimeError):
        module().verify_defaults([(['default_transaction_read_only=on','search_path=other'],)])


@pytest.mark.parametrize('verified',[False,None])
def test_failure_does_not_produce_a_maintenance_release_plan(verified):
    with pytest.raises(RuntimeError):
        module().release_plan(verified)


def test_only_verified_integrity_allows_reopening():
    assert module().release_plan(True)==('reset_readonly','allow_connections')


def test_expected_driver_wrapped_refusal_is_recognized_only_with_catalog_barrier():
    m=module()
    assert getattr(m,'is_expected_refusal',lambda *args:False)(
        'connection failed: database is not currently accepting connections',False)
    assert not m.is_expected_refusal('connection refused',False)
    assert not m.is_expected_refusal('database is not currently accepting connections',True)
