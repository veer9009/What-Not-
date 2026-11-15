"""Recovery must allow idle clients without overlooking transaction risks."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'docs/security/rehearse_auth_recovery.py'
spec = importlib.util.spec_from_file_location('auth_recovery', SCRIPT)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def assess(rows):
    guard = getattr(recovery, 'assess_source_sessions', None)
    assert callable(guard), 'Recovery needs a transaction-aware session guard'
    return guard(rows)


def test_ordinary_idle_client_does_not_block_consistent_backup():
    result = assess([('idle', False, False, 1)])
    assert result['safe_to_snapshot'] is True
    assert result['ordinary_idle_sessions'] == 1
    assert result['future_writes_excluded'] is False


@pytest.mark.parametrize('row', [
    ('idle in transaction', True, False, 1),
    ('idle in transaction (aborted)', True, False, 1),
    ('active', True, False, 1),
    ('active', False, False, 1),
    ('idle', False, True, 1),
    (None, False, False, 1),
])
def test_transaction_or_unobservable_session_requires_review(row):
    result = assess([('idle', False, False, 2), row])
    assert result['safe_to_snapshot'] is False
    assert result['ordinary_idle_sessions'] == 2
    assert result['risk_session_count'] == 1


def test_no_other_sessions_does_not_guarantee_future_quiescence():
    result = assess([])
    assert result['safe_to_snapshot'] is True
    assert result['future_writes_excluded'] is False
