"""Offline safety checks. No EC2, application database, service or real mail."""
import hashlib
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

AUTOMATION = Path(__file__).resolve().parents[1]
SHA = 'a' * 40


@pytest.fixture
def module():
    source = AUTOMATION / 'beta_automation.py'
    assert source.is_file(), 'Read-only automation engine has not been implemented'
    spec = importlib.util.spec_from_file_location('beta_automation', source)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class FakeRunner:
    def __init__(self):
        self.responses = {}
        self.calls = []

    def run(self, args, **kwargs):
        self.calls.append((args, kwargs))
        response = self.responses[tuple(args)]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def setup(module, tmp_path):
    release = tmp_path / 'release'
    release.mkdir()
    (release / 'backend').mkdir()
    runner = FakeRunner()
    inventory = {
        'format_version': 1, 'operator': 'ubuntu', 'machine_id': '1' * 32,
        'release_commit': SHA, 'release_path': str(release),
        'live_commit': 'b' * 40, 'live_state_sha256': 'c' * 64,
        'live_path': '/home/ubuntu/What-Not-',
        'rehearsal_path': '/home/ubuntu/whatnot-predeploy-20261123',
        'domain': 'avetest.online', 'upstream': '127.0.0.1:8001',
        'frontend_root': '/var/www/html',
        'database': {'name': 'whatnot_pilot_beta', 'oid': 1234,
                     'system_identifier': '987654321', 'server_addr': '127.0.0.1',
                     'server_port': 5432, 'role': 'whatnot_preflight',
                     'revision': '0010', 'major': 18, 'service': 'whatnot_preflight'},
        'evidence': {}, 'minimum_free_bytes': 5 * 1024**3,
        'deployment_state': 'never_started',
    }
    checker = module.Preflight(inventory, runner)
    return SimpleNamespace(module=module, inv=inventory, checker=checker,
                           runner=runner, root=tmp_path, release=release)


def evidence(setup, kind, data):
    data = {'review_id': 'offline-fixture', **data}
    path = setup.root / (kind + '.json')
    path.write_text(json.dumps(data), encoding='utf-8')
    path.chmod(0o600)
    setup.inv['evidence'][kind] = {'path': str(path),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return path


def release_responses(s):
    base = ['git', '-C', str(s.release)]
    s.runner.responses[tuple(base + ['config', '--includes', '--null', '--list'])] = ''
    s.runner.responses[tuple(base + ['rev-parse', 'HEAD'])] = SHA + '\n'
    s.runner.responses[tuple(base + ['status', '--porcelain=v1', '--untracked-files=all'])] = ''


def test_wrong_server_is_rejected(setup, monkeypatch):
    monkeypatch.setattr(setup.module, 'host_facts', lambda: ('Ubuntu', 'ubuntu', '2' * 32))
    with pytest.raises(setup.module.Blocker):
        setup.checker.server()


def test_wrong_operator_is_rejected(setup, monkeypatch):
    monkeypatch.setattr(setup.module, 'host_facts', lambda: ('Ubuntu', 'root', '1' * 32))
    with pytest.raises(setup.module.Blocker):
        setup.checker.server()


@pytest.mark.parametrize('dirty', [' M backend/app/core/config.py\n', '?? secret.env\n'])
def test_dirty_release_is_rejected(setup, dirty):
    release_responses(setup)
    setup.runner.responses[('git', '-C', str(setup.release), 'status', '--porcelain=v1', '--untracked-files=all')] = dirty
    with pytest.raises(setup.module.Blocker):
        setup.checker.release()


def test_clean_approved_release_is_accepted(setup):
    release_responses(setup)
    setup.checker.release()


def test_release_identity_is_checked_before_executable_dependencies(module):
    assert module.CHECKS.index('release') < module.CHECKS.index('tools')


def test_git_process_filters_are_rejected_before_status(setup):
    release_responses(setup)
    setup.runner.responses[('git', '-C', str(setup.release), 'config', '--includes', '--null', '--list')] = 'filter.unsafe.process\nsecret-command\0'
    with pytest.raises(setup.module.Blocker):
        setup.checker.release()
    assert not any('status' in call[0] for call in setup.runner.calls)


def test_report_cannot_be_written_in_live_checkout_with_wrong_inventory(module):
    with pytest.raises(module.Blocker):
        module.report_destination('/home/ubuntu/What-Not-/private-reports', {'live_path': '/wrong'})


def test_dependencies_are_copied_and_changes_stay_disposable(setup):
    source = setup.root / 'installed'
    source.mkdir()
    (source / 'module.js').write_text('original')
    destination = setup.root / 'snapshot/node_modules'
    destination.parent.mkdir()
    setup.module.copy_dependencies(source, destination)
    (destination / 'module.js').write_text('changed by a test')
    assert (source / 'module.js').read_text() == 'original'
    assert not destination.is_symlink()


def test_worktree_scoped_filters_are_checked(setup, monkeypatch):
    def config(args, **options):
        # Local scope alone omits a worktree's executable conversion setting.
        return '' if '--local' in args else 'filter.worktree.clean\nunsafe-process\0'
    monkeypatch.setattr(setup.runner, 'run', config)
    with pytest.raises(setup.module.Blocker):
        setup.checker.safe_git(setup.release)


def test_ambient_temp_paths_are_not_propagated(module, monkeypatch):
    for key in ('TEMP', 'TMP', 'TMPDIR'):
        monkeypatch.setenv(key, '/home/ubuntu/What-Not-/unsafe-temp')
    assert not {'TEMP', 'TMP', 'TMPDIR'} & set(module.clean_environment())


def test_linux_temporary_parent_ignores_ambient_temp(module, monkeypatch):
    monkeypatch.setenv('TMPDIR', '/home/ubuntu/What-Not-/unsafe-temp')
    monkeypatch.setattr(module.platform, 'system', lambda: 'Linux')
    assert module.temporary_location() == Path('/tmp')


def test_runner_discards_failing_process_output(module, capfd):
    with pytest.raises(module.Blocker):
        module.Runner().run([sys.executable, '-c',
            "import sys; print('SENTINEL-CREDENTIAL'); print('SENTINEL-CREDENTIAL',file=sys.stderr);sys.exit(1)"])
    captured = capfd.readouterr()
    assert 'SENTINEL-CREDENTIAL' not in captured.out + captured.err


def test_timeout_report_does_not_echo_command_or_output(setup, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(['SENTINEL-CREDENTIAL'], 1,
            output='SENTINEL-CREDENTIAL', stderr='SENTINEL-CREDENTIAL')
    monkeypatch.setattr(setup.checker, 'nginx', timeout)
    report = setup.checker.run(only=['nginx'])
    assert report['checks'][0]['status'] == 'FAIL'
    assert 'SENTINEL-CREDENTIAL' not in json.dumps(report)


@pytest.mark.parametrize('tamper', [None, 'missing', 'stale', 'hash', 'wrong_database'])
def test_backup_evidence_and_archive_are_checked(setup, tamper):
    archive = setup.root / 'synthetic.dump'
    archive.write_bytes(b'synthetic-archive')
    archive.chmod(0o600)
    setup.inv['backup_directory'] = str(setup.root)
    now = datetime.now(timezone.utc)
    data = {'release_commit': SHA, 'status': 'PASS',
        'database': dict(setup.inv['database']), 'revision': '0010',
        'restore_status': 'PASS', 'restored_database': 'disposable_clone',
        'business_counts_match': True, 'archive_integrity_verified': True,
        'created_at': (now - timedelta(minutes=5)).isoformat(),
        'restored_at': (now - timedelta(minutes=1)).isoformat(),
        'archive_path': str(archive), 'archive_sha256': setup.module.digest(archive)}
    if tamper == 'missing':
        archive.unlink()
    elif tamper == 'stale':
        data['created_at'] = (now - timedelta(days=2)).isoformat()
    elif tamper == 'hash':
        archive.write_bytes(b'changed')
    elif tamper == 'wrong_database':
        data['database']['name'] = 'wrong'
    evidence(setup, 'backup', data)
    setup.runner.responses[('pg_restore', '--list', str(archive))] = 'synthetic list'
    if tamper:
        with pytest.raises(setup.module.Blocker):
            setup.checker.backup()
    else:
        setup.checker.backup()


@pytest.mark.parametrize('revision_only', [False, True])
def test_schema_compatible_rollback_requires_behavioral_evidence(setup, revision_only):
    root = setup.root / 'rollback'
    root.mkdir()
    setup.inv['rollback_path'] = str(root)
    result = setup.root / 'rollback-tests.json'
    result.write_text('{"synthetic_results":"PASS"}')
    result.chmod(0o600)
    data = {'release_commit': SHA, 'status': 'PASS', 'path': str(root),
        'commit': 'd' * 40, 'schema': '0012', 'revision_only_change': revision_only,
        'passed_checks': ['readiness', 'authentication', 'sessions', 'buyer', 'seller',
            'admin', 'business_preservation', 'audit_preservation', 'recovery_preservation'],
        'isolated_database': 'disposable_clone', 'test_evidence_path': str(result),
        'test_evidence_sha256': setup.module.digest(result)}
    evidence(setup, 'rollback', data)
    setup.runner.responses[('git', '-C', str(root), 'config', '--includes', '--null', '--list')] = ''
    setup.runner.responses[('git', '-C', str(root), 'rev-parse', 'HEAD')] = 'd' * 40
    setup.runner.responses[('git', '-C', str(root), 'status', '--porcelain=v1', '--untracked-files=all')] = ''
    if revision_only:
        with pytest.raises(setup.module.Blocker):
            setup.checker.rollback()
    else:
        setup.checker.rollback()


@pytest.mark.parametrize('field,value', [('name', 'wrong_database'), ('oid', 9),
    ('revision', '0012'), ('server_addr', '192.0.2.7'), ('system_identifier', 'other'),
    ('read_only', 'off'), ('major', 17)])
def test_wrong_database_or_schema_is_rejected(setup, monkeypatch, field, value):
    observed = dict(setup.inv['database'], read_only='on')
    observed[field] = value
    monkeypatch.setattr(setup.checker, 'database_observation', lambda: observed)
    with pytest.raises(setup.module.Blocker):
        setup.checker.database()


def test_matching_read_only_database_is_accepted(setup, monkeypatch):
    observed = dict(setup.inv['database'], read_only='on')
    monkeypatch.setattr(setup.checker, 'database_observation', lambda: observed)
    setup.checker.database()


@pytest.mark.parametrize('kind', ['backup', 'rollback', 'maintenance', 'credentials', 'reconciliation'])
def test_missing_required_evidence_is_rejected(setup, kind):
    with pytest.raises(setup.module.Blocker):
        setup.checker.review(kind)


def test_evidence_is_bound_to_commit_and_bytes(setup):
    path = evidence(setup, 'maintenance', {'release_commit': SHA, 'status': 'PASS'})
    assert setup.checker.review('maintenance')['status'] == 'PASS'
    path.write_text('{}')
    with pytest.raises(setup.module.Blocker):
        setup.checker.review('maintenance')


def test_missing_frontend_artifact_is_rejected(setup):
    with pytest.raises(setup.module.Blocker):
        setup.checker.frontend()


@pytest.mark.parametrize('state', ['completed', 'interrupted', 'migration_failed',
    'backend_start_failed', 'nginx_validation_failed'])
def test_prior_failure_or_repeated_deployment_requires_review(setup, state):
    setup.inv['deployment_state'] = state
    with pytest.raises(setup.module.Blocker):
        setup.checker.history()


def test_same_live_and_release_commit_is_repeated_deployment(setup):
    setup.inv['live_commit'] = SHA
    with pytest.raises(setup.module.Blocker):
        setup.checker.history()


def test_failed_nginx_probe_is_closed_and_output_not_logged(setup):
    setup.runner.responses[('sudo', '-n', 'nginx', '-T')] = RuntimeError('SECRET_TOKEN=do-not-print')
    with pytest.raises(Exception):
        setup.checker.nginx()
    report = setup.checker.run(only=['nginx'])
    assert report['status'] == 'FAIL'
    assert 'SECRET_TOKEN' not in json.dumps(report)


def test_all_read_only_checks_cannot_unlock_live_apply(setup, monkeypatch):
    for name in setup.module.CHECKS:
        monkeypatch.setattr(setup.checker, name, lambda: None)
    report = setup.checker.run()
    assert report['status'] == 'FAIL'
    assert report['live_apply_supported'] is False
    assert any(g['gate'] == 'live_adapter' and g['status'] == 'BLOCKED' for g in report['checks'])


def test_wrong_server_prevents_all_later_probes(setup, monkeypatch):
    monkeypatch.setattr(setup.module, 'host_facts', lambda: ('Ubuntu', 'ubuntu', '2' * 32))
    for name in setup.module.CHECKS[1:]:
        monkeypatch.setattr(setup.checker, name, lambda: pytest.fail('Probe ran on wrong server'))
    report = setup.checker.run()
    assert report['checks'][0] == {'gate': 'server', 'status': 'FAIL'}
    assert all(g['status'] == 'BLOCKED' for g in report['checks'][1:])


def test_psql_is_read_only_passwordless_and_does_not_inherit_secrets(setup, monkeypatch):
    service = setup.root / 'pg_service.conf'
    password = setup.root / 'pgpass'
    for path in (service, password):
        path.write_text('synthetic fixture')
        path.chmod(0o600)
    setup.inv['database'].update(service_file=str(service), pass_file=str(password))
    monkeypatch.setenv('PGPASSWORD', 'SENTINEL-CREDENTIAL')
    observed = []
    def query(args, **options):
        observed.append((args, options))
        return '{}'
    monkeypatch.setattr(setup.runner, 'run', query)
    setup.checker.database_observation()
    args, options = observed[0]
    assert args[:3] == ['psql', '-X', '--no-password']
    assert '--dbname=service=whatnot_preflight' in args
    assert 'default_transaction_read_only=on' in options['env']['PGOPTIONS']
    assert 'statement_timeout=5000' in options['env']['PGOPTIONS']
    assert 'SENTINEL-CREDENTIAL' not in json.dumps(options)
    assert not any(word in args[-1].upper() for word in ['INSERT ', 'UPDATE ', 'DELETE ', 'ALTER ', 'DROP '])


def test_unreconciled_ec2_files_block_before_reading_live_files(setup):
    evidence(setup, 'reconciliation', {'release_commit': SHA, 'status': 'PASS', 'files': {}})
    with pytest.raises(setup.module.Blocker):
        setup.checker.reconciliation()


@pytest.mark.parametrize('installed', [{'cryptography': '48.0.0'}, {}])
def test_missing_or_wrong_pinned_dependency_blocks(setup, monkeypatch, installed):
    (setup.release / 'backend/requirements.txt').write_text('cryptography==49.0.0\n')
    setup.inv['release_python'] = '/reviewed/python'
    monkeypatch.setattr(setup.runner, 'run', lambda *args, **kwargs: json.dumps(installed))
    with pytest.raises(setup.module.Blocker):
        setup.checker.dependencies()


@pytest.mark.parametrize('tamper', ['stale', 'commit', 'inventory'])
def test_dry_run_report_binding_rejects_stale_or_wrong_inputs(setup, tamper):
    inv = setup.root / 'inventory.json'
    inv.write_text(json.dumps(setup.inv))
    inv.chmod(0o600)
    data = {'format_version': 1, 'operation': 'preflight', 'status': 'FAIL',
        'release_commit': SHA, 'inventory_sha256': setup.module.digest(inv),
        'created_at': datetime.now(timezone.utc).isoformat()}
    if tamper == 'stale':
        data['created_at'] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    elif tamper == 'commit':
        data['release_commit'] = 'd' * 40
    else:
        data['inventory_sha256'] = 'e' * 64
    report = setup.root / 'report.json'
    report.write_text(json.dumps(data))
    report.chmod(0o600)
    with pytest.raises(setup.module.Blocker):
        setup.module.bound_report(inv, report)


@pytest.mark.parametrize('mode', ['deploy', 'rollback'])
@pytest.mark.parametrize('apply', [False, True])
def test_live_operations_are_unconditionally_blocked(module, tmp_path, mode, apply):
    inv = tmp_path / 'inventory.json'
    inv.write_text(json.dumps({'release_commit': SHA, 'password': 'SENTINEL-CREDENTIAL'}))
    report = tmp_path / 'forged-pass.json'
    report.write_text(json.dumps({'status': 'PASS', 'release_commit': SHA}))
    args = [sys.executable, '-I', '-B', str(AUTOMATION / 'beta_automation.py'), mode,
            '--inventory', str(inv), '--preflight-report', str(report)]
    if apply:
        args.append('--apply')
    result = subprocess.run(args, capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert 'BLOCKED' in result.stdout
    assert 'SENTINEL-CREDENTIAL' not in result.stdout + result.stderr
    assert inv.read_text().find('SENTINEL-CREDENTIAL') >= 0


def test_invalid_inventory_does_not_echo_secret(module, tmp_path):
    inv = tmp_path / 'bad.json'
    inv.write_text('postgresql://user:SENTINEL-CREDENTIAL@host/database')
    result = subprocess.run([sys.executable, '-I', '-B', str(AUTOMATION / 'beta_automation.py'),
        'preflight', '--inventory', str(inv), '--report-dir', str(tmp_path)],
        capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert 'SENTINEL-CREDENTIAL' not in result.stdout + result.stderr


def test_cli_argument_errors_are_redacted(module):
    result = subprocess.run([sys.executable, '-I', '-B', str(AUTOMATION / 'beta_automation.py'),
        'preflight', '--password=SENTINEL-CREDENTIAL'], capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert 'SENTINEL-CREDENTIAL' not in result.stdout + result.stderr


def test_clean_environment_strips_live_database_and_provider_settings(module, monkeypatch):
    for name in ['DATABASE_URL', 'PGPASSWORD', 'WHAT_NOT_JWT_SECRET_KEY', 'AWS_SECRET_ACCESS_KEY', 'PYTHONPATH', 'BASH_ENV', 'NODE_OPTIONS']:
        monkeypatch.setenv(name, 'SENTINEL-CREDENTIAL')
    env = module.clean_environment()
    assert 'SENTINEL-CREDENTIAL' not in json.dumps(env)


def test_entrypoints_do_not_contain_mutation_commands(module):
    for name, mode in [('preflight.sh', 'preflight'), ('deploy-beta.sh', 'deploy'), ('rollback-beta.sh', 'rollback')]:
        text = (AUTOMATION / name).read_text()
        assert 'set -euo pipefail' in text
        assert 'set +x' in text
        assert 'beta_automation.py' in text and mode in text
        assert not any(command in text for command in ['git pull', 'git reset', 'git clean', 'systemctl restart', 'alembic upgrade', 'pg_restore'])


def test_migration_and_startup_failures_are_not_simulated_as_success(module):
    # The placeholder never executes these stages. This does NOT verify a real
    # migration/startup failure handler; that remains blocked integration work.
    text = (AUTOMATION / 'beta_automation.py').read_text()
    assert 'LIVE_APPLY_SUPPORTED = False' in text
    assert "'alembic', 'upgrade'" not in text
    assert "'systemctl', 'start'" not in text


def bash_path():
    path = Path('C:/Program Files/Git/bin/bash.exe') if os.name == 'nt' else Path(shutil.which('bash') or '/nonexistent')
    if not path.is_file():
        pytest.skip('Bash unavailable; Python safety tests still run')
    return str(path)


@pytest.mark.parametrize('script', ['preflight.sh', 'deploy-beta.sh', 'rollback-beta.sh'])
def test_bash_syntax(module, script):
    result = subprocess.run([bash_path(), '--noprofile', '--norc', '-n',
        (AUTOMATION / script).as_posix()], capture_output=True, timeout=10)
    assert result.returncode == 0


@pytest.mark.parametrize('script', ['deploy-beta.sh', 'rollback-beta.sh'])
@pytest.mark.parametrize('apply', [False, True])
def test_bash_entrypoints_remain_blocked(module, tmp_path, script, apply):
    env = dict(os.environ, WHATNOT_AUTOMATION_PYTHON=Path(sys.executable).as_posix())
    args = [bash_path(), '--noprofile', '--norc', (AUTOMATION / script).as_posix(),
            '--inventory', str(tmp_path / 'not-provided.json'),
            '--preflight-report', str(tmp_path / 'not-provided-report.json')]
    if apply:
        args.append('--apply')
    result = subprocess.run(args, capture_output=True, text=True, env=env, timeout=10)
    assert result.returncode == 2
    assert json.loads(result.stdout)['status'] == 'BLOCKED'
