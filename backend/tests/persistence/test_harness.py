"""Failure-path checks use simulated process outcomes, never a database."""
from pathlib import Path
import shutil
import subprocess

import pytest
import conftest as harness


@pytest.mark.parametrize("failure", [RuntimeError("startup failed"), subprocess.TimeoutExpired("pg_ctl", 30)])
def test_failed_start_stops_surviving_server_before_cleanup(monkeypatch, failure):
    actions = []
    owned_root = None

    def run(binary, *args, **kwargs):
        nonlocal owned_root
        if binary == "initdb":
            data = Path(args[1])
            data.mkdir()
            owned_root = data.parent
            return 0
        action = args[-1]
        actions.append(action)
        if action == "start":
            (owned_root / "data" / "postmaster.pid").write_text("simulated", encoding="utf-8")
            raise failure
        if action == "status":
            return 3 if "stop" in actions else 0
        return 0

    monkeypatch.setattr(harness, "run_pg", run)
    with pytest.raises(type(failure)):
        next(harness.isolated_cluster.__wrapped__())
    assert "stop" in actions, "A surviving server must be stopped after failed startup"
    assert actions[-1] == "status", "Confirm shutdown before deleting cluster files"
    assert not owned_root.exists()


def test_shutdown_failure_retains_cluster_files(monkeypatch):
    owned_root = None

    def run(binary, *args, **kwargs):
        nonlocal owned_root
        if binary == "initdb":
            data = Path(args[1])
            data.mkdir()
            owned_root = data.parent
            return 0
        action = args[-1]
        if action == "start":
            raise RuntimeError("startup failed after spawn")
        if action == "status":
            return 0
        if action == "stop":
            raise RuntimeError("shutdown failed")
        return 0

    monkeypatch.setattr(harness, "run_pg", run)
    try:
        with pytest.raises(RuntimeError, match="shutdown failed"):
            next(harness.isolated_cluster.__wrapped__())
        assert owned_root.exists(), "Unconfirmed shutdown must never delete cluster files"
    finally:
        # No server was launched by this simulated runner. Remove only its generated directory.
        if owned_root and owned_root.exists():
            assert owned_root.name.startswith("whatnot-phase3-postgres-")
            shutil.rmtree(owned_root)
