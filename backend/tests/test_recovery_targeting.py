"""A misspelled, replaced or original database must never pass a write guard."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('recovery_existing',
    Path(__file__).resolve().parents[2] / 'docs/security/rehearse_existing_server.py')


@pytest.mark.parametrize('actual', [
    ('whatnot_app_dev', 41, True),
    ('whatnot_rehearsal_20261115_a7e394c2', 99, True),
    ('whatnot_rehearsal_20261115_a7e394c2', 42, False),
])
def test_wrong_database_oid_or_owner_is_rejected(actual):
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(RuntimeError):
        module.verify_identity(actual, 'whatnot_rehearsal_20261115_a7e394c2', 42)


def test_verified_rehearsal_target_is_allowed():
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify_identity(('whatnot_rehearsal_20261115_a7e394c2', 42, True),
                           'whatnot_rehearsal_20261115_a7e394c2', 42)
