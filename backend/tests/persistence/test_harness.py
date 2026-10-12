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


def test_failed_initdb_retains_owned_files_without_deleting_possible_child_data(monkeypatch):
    owned_root = None

    def run(binary, *args, **kwargs):
        nonlocal owned_root
        assert binary == 'initdb'
        data = Path(args[1])
        data.mkdir()
        owned_root = data.parent
        raise RuntimeError('Bootstrap child may still be running')

    monkeypatch.setattr(harness, 'run_pg', run)
    try:
        with pytest.raises(RuntimeError, match='Bootstrap child'):
            next(harness.isolated_cluster.__wrapped__())
        assert owned_root.exists(), 'Do not delete files when bootstrap child termination is unconfirmed'
    finally:
        # This simulated runner creates no process; its generated files are safe to remove.
        if owned_root and owned_root.exists():
            assert owned_root.name.startswith('whatnot-phase3-postgres-')
            shutil.rmtree(owned_root)


def test_failed_fast_shutdown_can_stop_owned_disposable_cluster_immediately(monkeypatch):
    owned_root = None
    stopped = False
    modes = []

    def run(binary, *args, **kwargs):
        nonlocal owned_root, stopped
        if binary == 'initdb':
            data = Path(args[1])
            data.mkdir()
            owned_root = data.parent
            return 0
        if args[-1] == 'start':
            raise RuntimeError('Deliberate startup failure after spawning')
        if args[-1] == 'status':
            return 3 if stopped else 0
        if args[-1] == 'stop':
            mode = args[args.index('-m') + 1]
            modes.append(mode)
            if mode == 'fast':
                raise RuntimeError('Checkpoint shutdown timed out')
            assert mode == 'immediate'
            stopped = True
            return 0
        raise AssertionError('Unexpected operation')

    monkeypatch.setattr(harness, 'run_pg', run)
    try:
        with pytest.raises(RuntimeError, match='Deliberate startup failure'):
            next(harness.isolated_cluster.__wrapped__())
        assert modes == ['fast', 'immediate']
        assert stopped and not owned_root.exists()
    finally:
        if owned_root and owned_root.exists():
            assert owned_root.name.startswith('whatnot-phase3-postgres-')
            shutil.rmtree(owned_root)
