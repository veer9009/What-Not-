"""Read-only Ubuntu release preflight and deliberately blocked live entrypoints.

Inventory is data, never executable configuration. No SSH, migration, service
mutation, credential decryption, live restore, or release activation is implemented.
Only fixed gate names/statuses reach reports; raw probe output never does.
"""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import uuid

LIVE_APPLY_SUPPORTED = False
CHECKS = ('server', 'release', 'tools', 'live', 'history', 'reconciliation',
          'credentials', 'database', 'nginx', 'systemd', 'capacity', 'backup',
          'rollback', 'maintenance', 'frontend', 'tests')
RECONCILE = (
    'backend/app/core/config.py', 'backend/app/services/abuse.py',
    'backend/tests/persistence/conftest.py',
    'backend/tests/persistence/test_beta_authentication.py',
    'backend/tests/test_beta_auth_configuration.py',
    'backend/tests/test_open_beta_registration.py',
)
DEPLOY_PLAN = (
    'verify_release_and_artifacts', 'verify_schema_0012_rollback',
    'verify_maintenance_and_all_writer_restart_barriers', 'fresh_protected_backup',
    'verify_archive_integrity', 'quiesce_all_writers_and_restart_paths',
    'final_quiesced_backup_and_isolated_restore_evidence',
    'reconfirm_database_identity_and_0010', 'reviewed_migrations_to_0012',
    'activate_reviewed_backend_without_changing_credential_loader',
    'publish_verified_frontend', 'install_only_reviewed_nginx_delta_preserving_8001',
    'validate_nginx_before_reload', 'start_approved_pilot_api',
    'verify_readiness_and_http_health', 'approved_buyer_seller_admin_smoke_tests',
    'restore_traffic_only_after_all_gates', 'protected_deployment_report',
)
ROLLBACK_PLAN = (
    'preserve_failed_release_and_journal', 'verify_current_database_and_revision',
    'verify_functionally_tested_schema_0012_rollback',
    'verify_maintenance_and_writer_restart_barriers',
    'activate_only_reviewed_schema_compatible_application_and_frontend',
    'verify_health_readiness_and_role_flows_before_traffic',
    'preserve_all_new_business_audit_and_recovery_records',
)


class Blocker(Exception):
    """A fixed gate failed. Exception text must never be rendered."""


def require(condition):
    if not condition:
        raise Blocker()


def digest(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink())
    value = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def private_file(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and path.is_file())
    if os.name == 'posix':
        info = path.stat()
        require(info.st_uid in {0, os.geteuid()} and not stat.S_IMODE(info.st_mode) & 0o077)
        # No other user may swap the inventory/evidence through writable parents.
        for parent in path.parents:
            mode = parent.stat().st_mode
            require(not mode & 0o022 or bool(mode & stat.S_ISVTX))
    return path


def read_json(path):
    path = private_file(path)
    require(path.stat().st_size <= 1024 * 1024)
    value = json.loads(path.read_text(encoding='utf-8'))
    require(isinstance(value, dict))
    return value


def clean_environment():
    # Deliberately omit PG*, DATABASE_URL, WHAT_NOT_*, AWS*, loader settings,
    # shell startup files, PYTHONPATH and NODE_OPTIONS.
    env = {key: os.environ[key] for key in ('PATH', 'SYSTEMROOT', 'WINDIR') if key in os.environ}
    env.update(LANG='C.UTF-8', LC_ALL='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_NOSYSTEM='1',
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_COUNT='2',
        GIT_CONFIG_KEY_0='core.fsmonitor', GIT_CONFIG_VALUE_0='false',
        GIT_CONFIG_KEY_1='core.untrackedCache', GIT_CONFIG_VALUE_1='false')
    return env


class Runner:
    def run_bytes(self, args, *, cwd=None, env=None, timeout=30, maximum=4 * 1024**2):
        parent = checked_temporary_location()
        with tempfile.TemporaryFile(dir=parent) as output, tempfile.TemporaryFile(dir=parent) as errors:
            result = subprocess.run(args, cwd=cwd, env=env or clean_environment(),
                stdin=subprocess.DEVNULL, stdout=output, stderr=errors, timeout=timeout,
                check=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            require(result.returncode == 0)
            require(output.tell() <= maximum)
            output.seek(0)
            return output.read(maximum + 1)

    def run(self, args, **kwargs):
        return self.run_bytes(args, **kwargs).decode('utf-8')


def host_facts():
    require(platform.system() == 'Linux')
    import pwd
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    require(release.get('ID', '').strip('"') == 'ubuntu')
    return 'Ubuntu', pwd.getpwuid(os.geteuid()).pw_name, Path('/etc/machine-id').read_text().strip()


def temporary_location():
    # Ubuntu never consumes ambient TMPDIR/TEMP/TMP, which could name live paths.
    return Path('/tmp') if platform.system() == 'Linux' else Path.home() / 'AppData/Local/Temp'


def checked_temporary_location():
    parent = report_destination(temporary_location(), {})
    require(parent.is_dir() and parent.is_absolute() and parent.resolve() == parent)
    if os.name == 'posix':
        info = parent.stat()
        require(info.st_uid in {0, os.geteuid()})
        require(not info.st_mode & 0o022 or bool(info.st_mode & stat.S_ISVTX))
    return parent


def copy_dependencies(source, destination):
    source, destination = Path(source), Path(destination)
    require(source.is_dir() and not source.is_symlink() and not destination.exists())
    size = 0
    for path in source.rglob('*'):
        if path.is_symlink():
            require(not Path(os.readlink(path)).is_absolute())
            require(path.resolve().is_relative_to(source.resolve()))
        elif path.is_file():
            size += path.stat().st_size
            require(size <= 1024**3)
        else:
            require(path.is_dir())
    # Preserve only relative internal links. Vite can write its config bundle
    # under node_modules/.vite-temp, so a link to release dependencies is unsafe.
    shutil.copytree(source, destination, symlinks=True)


def report_destination(directory, inventory):
    # Fixed exclusions are independent of an invalid/untrusted inventory.
    roots = ['/home/ubuntu/What-Not-', '/home/ubuntu/whatnot-predeploy-20261123',
             '/home/ubuntu/What-Not-releases', '/var/www', '/etc',
             '/usr/local/lib/whatnot-pilot']
    roots.extend(inventory.get(key) for key in ('live_path', 'release_path',
        'rehearsal_path', 'frontend_root', 'rollback_path', 'backup_directory'))
    target = PurePosixPath(str(directory).replace('\\', '/'))
    for root in filter(None, roots):
        require(not target.is_relative_to(PurePosixPath(str(root).replace('\\', '/'))))
    return Path(directory)


def bound_report(inventory_path, report_path):
    inventory, report = read_json(inventory_path), read_json(report_path)
    require(report['format_version'] == 1 and report['operation'] == 'preflight')
    require(report['release_commit'] == inventory['release_commit'])
    require(re.fullmatch(r'[0-9a-f]{40}', inventory['release_commit']))
    require(report['inventory_sha256'] == digest(inventory_path))
    created = datetime.fromisoformat(report['created_at'])
    now = datetime.now(timezone.utc)
    require(now - timedelta(hours=1) <= created <= now)
    # This implementation never emits PASS. A fabricated PASS is not an approval.
    require(report['status'] == 'FAIL')
    return report


class Preflight:
    def __init__(self, inventory, runner=None):
        self.inv = inventory
        self.runner = runner or Runner()
        self.root = Path(inventory.get('release_path', '/nonexistent'))

    def git(self, path, *args):
        return self.runner.run(['git', '-C', str(path), *args]).strip()

    def safe_git(self, path):
        # Effective configuration includes config.worktree; --local omits it.
        configuration = self.git(path, 'config', '--includes', '--null', '--list')
        for item in configuration.split('\0'):
            key = item.partition('\n')[0].lower()
            require(not key.startswith('filter.'))

    def review(self, kind):
        try:
            ref = self.inv['evidence'][kind]
            require(re.fullmatch(r'[0-9a-f]{64}', ref['sha256']))
            require(digest(private_file(ref['path'])) == ref['sha256'])
            data = read_json(ref['path'])
            require(data['release_commit'] == self.inv['release_commit'] and data['status'] == 'PASS')
            require(bool(data.get('review_id')))
            return data
        except Exception:
            raise Blocker() from None

    def server(self):
        i = self.inv
        require(i['format_version'] == 1 and i['operator'] == 'ubuntu')
        require(re.fullmatch(r'[0-9a-f]{32}', i['machine_id']))
        require(host_facts() == ('Ubuntu', i['operator'], i['machine_id']))
        require(i['live_path'] == '/home/ubuntu/What-Not-')
        require(i['rehearsal_path'] == '/home/ubuntu/whatnot-predeploy-20261123')
        require(i['domain'] == 'avetest.online' and i['upstream'] == '127.0.0.1:8001')
        require(i['frontend_root'] == '/var/www/html')

    def tools(self):
        self.release()
        for tool in ('git', 'psql', 'pg_restore', 'nginx', 'systemctl', 'sudo', 'node'):
            require(shutil.which(tool))
        for tool in ('psql', 'pg_restore'):
            require(re.search(r'\b18(?:\.|\b)', self.runner.run([tool, '--version'])))
        require(self.root.is_absolute())
        executable = Path(self.inv['release_python'])
        # A normal Linux venv Python symlinks to the installed interpreter.
        require(executable.is_absolute() and executable.is_file()
                and executable.absolute().is_relative_to(self.root))
        require(self.runner.run([str(executable), '-I', '-B', '-c',
            'import sys; print(".".join(map(str, sys.version_info[:3])))']).strip() == '3.14.4')
        self.runner.run([str(executable), '-I', '-B', '-m', 'pip', 'check'], timeout=60)
        self.dependencies()

    def dependencies(self):
        expected = {}
        for line in (self.root / 'backend/requirements.txt').read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#'):
                match = re.fullmatch(r'([A-Za-z0-9_-]+)(?:\[[A-Za-z0-9_,.-]+\])?==([A-Za-z0-9_.+-]+)', line.strip())
                require(match is not None)
                expected[match[1]] = match[2]
        require(bool(expected))
        script = ('import importlib.metadata as m,json; names=' + repr(list(expected)) +
                  '; print(json.dumps({n:m.version(n) for n in names}))')
        installed = json.loads(self.runner.run([self.inv['release_python'], '-I', '-B', '-c', script]))
        require(installed == expected)

    def release(self):
        require(re.fullmatch(r'[0-9a-f]{40}', self.inv['release_commit']))
        require(self.root.is_absolute() and self.root.is_dir() and self.root.resolve() == self.root)
        for name in ('live_path', 'rehearsal_path', 'frontend_root'):
            other = Path(self.inv[name]).resolve()
            require(not self.root.is_relative_to(other) and not other.is_relative_to(self.root))
        self.safe_git(self.root)
        require(self.git(self.root, 'rev-parse', 'HEAD') == self.inv['release_commit'])
        require(not self.git(self.root, 'status', '--porcelain=v1', '--untracked-files=all'))

    def live(self):
        path = Path(self.inv['live_path'])
        self.safe_git(path)
        require(self.git(path, 'rev-parse', 'HEAD') == self.inv['live_commit'])
        require(self.git(path, 'branch', '--show-current') == 'feature/open-beta-registration')
        status = self.runner.run(['git', '-C', str(path), 'status', '--porcelain=v1', '--untracked-files=all'])
        delta = self.runner.run(['git', '-C', str(path), 'diff', '--no-ext-diff', '--no-textconv', 'HEAD', '--binary'])
        value = hashlib.sha256((status + '\0' + delta).encode())
        names = self.runner.run(['git', '-C', str(path), 'ls-files', '--others', '--exclude-standard', '-z'])
        for name in sorted(filter(None, names.split('\0'))):
            child = path / name
            require(child.resolve().is_relative_to(path.resolve()) and child.is_file() and not child.is_symlink())
            value.update(name.encode() + b'\0' + digest(child).encode())
        require(value.hexdigest() == self.inv['live_state_sha256'])

    def history(self):
        require(self.inv['deployment_state'] == 'never_started')
        require(self.inv['live_commit'] != self.inv['release_commit'])
        # An existing deployment journal must be reviewed, never overwritten.
        journal = Path(self.inv.get('journal_path', '/nonexistent'))
        require(journal.is_absolute() and not journal.exists())

    def reconciliation(self):
        data = self.review('reconciliation')
        require(set(data['files']) == set(RECONCILE))
        for name in RECONCILE:
            record = data['files'][name]
            require(record['release_sha256'] == record['ec2_sha256'])
            require(digest(self.root / name) == record['release_sha256'])
            require(digest(Path(self.inv['rehearsal_path']) / name) == record['ec2_sha256'])
        require(data['open_beta_registration_reviewed'] is True and data['abuse_protection_reviewed'] is True)

    def credentials(self):
        data = self.review('credentials')
        require(data['loader_unchanged'] is True and data['recovery_email_enabled'] is False)
        require(digest('/usr/local/lib/whatnot-pilot/pilot_asgi.py') == self.inv['loader_sha256'])
        private_file(self.inv['database']['service_file'])
        private_file(self.inv['database']['pass_file'])
        # This validates only protected input/evidence, never decrypts a systemd
        # credential or proves the unknown loader accepts the new release.

    def database_observation(self):
        d = self.inv['database']
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,64}', d['service']))
        env = clean_environment()
        env.update(PGSERVICEFILE=str(private_file(d['service_file'])),
            PGPASSFILE=str(private_file(d['pass_file'])),
            PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=2000',
            PGCONNECT_TIMEOUT='5')
        query = """SELECT json_build_object('name',current_database(),'oid',d.oid::bigint,
            'system_identifier',(pg_control_system()).system_identifier::text,
            'server_addr',host(inet_server_addr()),'server_port',inet_server_port(),
            'role',current_user,'revision',(SELECT version_num FROM alembic_version),
            'major',current_setting('server_version_num')::integer/10000,
            'read_only',current_setting('transaction_read_only'))
            FROM pg_database d WHERE d.datname=current_database()"""
        return json.loads(self.runner.run(['psql', '-X', '--no-password', '--no-align',
            '--tuples-only', '--set=ON_ERROR_STOP=1', '--dbname=service=' + d['service'],
            '--command', query], env=env, timeout=15))

    def database(self):
        d = self.inv['database']
        require(d['name'] == 'whatnot_pilot_beta' and d['revision'] == '0010' and d['major'] == 18)
        require(isinstance(d['oid'], int) and d['oid'] > 0)
        seen = self.database_observation()
        for field in ('name', 'oid', 'system_identifier', 'server_addr', 'server_port', 'role', 'revision', 'major'):
            require(seen[field] == d[field])
        require(seen['read_only'] == 'on')

    def nginx(self):
        raw = self.runner.run(['sudo', '-n', 'nginx', '-T'])
        require(hashlib.sha256(raw.encode()).hexdigest() == self.inv['nginx_sha256'])
        require(Path('/etc/nginx/sites-enabled/default').resolve() == Path('/etc/nginx/sites-available/default'))
        # Fingerprint binds an independently reviewed effective configuration.
        # These conservative checks do not replace review of nginx inheritance.
        content = re.sub(r'(?m)#.*$', '', raw)
        require(re.search(r'server_name\s+[^;]*\bavetest\.online\b[^;]*;', content))
        require(re.search(r'root\s+/var/www/html\s*;', content))
        targets = re.findall(r'proxy_pass\s+([^;]+);', content)
        require(targets and all(t.strip() == 'http://127.0.0.1:8001' for t in targets))
        require('blob:' in content and re.search(r'client_max_body_size\s+5m\s*;', content))

    def systemd(self):
        properties = 'FragmentPath,DropInPaths,User,WorkingDirectory,ExecStart,LoadCredentialEncrypted'
        for unit, key in [('whatnot-pilot-api.service', 'pilot_unit_sha256'), ('whatnot-api.service', 'secondary_unit_sha256')]:
            raw = self.runner.run(['systemctl', 'show', unit, '--no-pager', '--property=' + properties])
            require(hashlib.sha256(raw.encode()).hexdigest() == self.inv[key])
            if unit == 'whatnot-pilot-api.service':
                require(re.search(r'(?m)^LoadCredentialEncrypted=.+$', raw))
                require('pilot_asgi' in raw and re.search(r'--port(?:=|\s+)8001\b', raw))
                self.runner.run(['systemctl', 'is-active', '--quiet', unit])

    def capacity(self):
        minimum = self.inv['minimum_free_bytes']
        require(isinstance(minimum, int) and minimum >= 5 * 1024**3)
        for path in (self.root, Path(self.inv['backup_directory']), Path(self.inv['frontend_root'])):
            require(shutil.disk_usage(path).free >= minimum)

    def backup(self):
        data = self.review('backup')
        require(data['database'] == self.inv['database'])
        require(data['revision'] == '0010' and data['restore_status'] == 'PASS')
        require(data['restored_database'] != self.inv['database']['name'])
        require(data['business_counts_match'] is True)
        require(data['archive_integrity_verified'] is True)
        created = datetime.fromisoformat(data['created_at'])
        restored = datetime.fromisoformat(data['restored_at'])
        now = datetime.now(timezone.utc)
        require(now - timedelta(hours=24) <= created <= restored <= now)
        archive = private_file(data['archive_path'])
        require(archive.parent == Path(self.inv['backup_directory']))
        require(digest(archive) == data['archive_sha256'])
        self.runner.run(['pg_restore', '--list', str(archive)], timeout=60)

    def rollback(self):
        data = self.review('rollback')
        path = Path(data['path'])
        require(str(path) == self.inv['rollback_path'])
        require(path.is_absolute() and path.is_dir() and path.resolve() == path and path != self.root)
        require(re.fullmatch(r'[0-9a-f]{40}', data['commit']))
        self.safe_git(path)
        require(self.git(path, 'rev-parse', 'HEAD') == data['commit'])
        require(not self.git(path, 'status', '--porcelain=v1', '--untracked-files=all'))
        require(data['schema'] == '0012' and data['revision_only_change'] is False)
        required = {'readiness', 'authentication', 'sessions', 'buyer', 'seller', 'admin',
                    'business_preservation', 'audit_preservation', 'recovery_preservation'}
        require(required <= set(data['passed_checks']))
        require(data['isolated_database'] != self.inv['database']['name'])
        require(bool(data['test_evidence_sha256']) and data['test_evidence_sha256'] == digest(private_file(data['test_evidence_path'])))

    def maintenance(self):
        data = self.review('maintenance')
        require({'whatnot-pilot-api.service', 'whatnot-api.service'} <= set(data['writer_units']))
        for key in ('traffic_barrier', 'all_writers', 'restart_paths', 'quiescence_probe', 'resume_procedure'):
            require(isinstance(data[key], str) and bool(data[key].strip()))

    def frontend(self):
        data = self.review('frontend')
        root = Path(data['path'])
        require(root.is_absolute() and root.is_dir() and root.resolve() == root)
        require(root != Path(self.inv['frontend_root']))
        require(data['production'] is True and data['api_base'] == '/api/v1')
        files = data['files']
        require('index.html' in files and any(n.endswith('.js') for n in files) and any(n.endswith('.css') for n in files))
        found = set()
        for path in root.rglob('*'):
            require(not path.is_symlink())
            if path.is_file():
                name = path.relative_to(root).as_posix()
                require(name in files and digest(path) == files[name])
                found.add(name)
        require(found == set(files))

    def tests(self):
        self.release()  # Never execute tests from an unapproved/dirty tree.
        data = self.review('isolated_tests')
        require(data['no_live_network_or_database'] is True)
        raw = self.runner.run_bytes(['git', '-C', str(self.root), 'archive', '--format=tar', self.inv['release_commit']], maximum=128 * 1024**2)
        with tempfile.TemporaryDirectory(prefix='whatnot-preflight-tests-', dir=checked_temporary_location()) as folder:
            snapshot = Path(folder)
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                members = archive.getmembers()
                for member in members:
                    dest = snapshot / member.name
                    require(dest.resolve().is_relative_to(snapshot.resolve()))
                    require(member.isfile() or member.isdir())
                    require(not (dest.name == '.env' or (dest.name.startswith('.env.') and not dest.name.endswith('.example'))))
                archive.extractall(snapshot, members=members, filter='data')
            require((self.root / 'node_modules/vitest/vitest.mjs').is_file())
            copy_dependencies(self.root / 'node_modules', snapshot / 'node_modules')
            env = clean_environment()
            temporary = snapshot / 'tmp'
            temporary.mkdir()
            env.update(HOME=folder, XDG_CACHE_HOME=str(snapshot / '.cache'),
                TMPDIR=str(temporary), TEMP=str(temporary), TMP=str(temporary), WHAT_NOT_ENVIRONMENT='test')
            self.runner.run([self.inv['release_python'], '-B', '-m', 'pytest', 'tests',
                '--ignore=tests/persistence', '--ignore=tests/session_integration',
                '-p', 'no:cacheprovider', '-q', '--tb=no'], cwd=snapshot / 'backend', env=env, timeout=600)
            self.runner.run(['node', str(snapshot / 'node_modules/vitest/vitest.mjs'), 'run', 'src',
                '--config', 'vite.config.ts', '--pool=threads', '--maxWorkers=1',
                '--no-file-parallelism', '--no-cache'], cwd=snapshot, env=env, timeout=1200)

    def run(self, only=None):
        checks = []
        stopped = False
        for name in only if only is not None else CHECKS:
            if stopped:
                checks.append({'gate': name, 'status': 'BLOCKED'})
                continue
            try:
                getattr(self, name)()
            except Exception:
                checks.append({'gate': name, 'status': 'FAIL'})
                stopped = True
            else:
                checks.append({'gate': name, 'status': 'PASS'})
        checks.append({'gate': 'live_adapter', 'status': 'BLOCKED'})
        commit = self.inv.get('release_commit', '')
        return {'format_version': 1, 'operation': 'preflight', 'status': 'FAIL',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'release_commit': commit if isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit) else None,
            'live_apply_supported': LIVE_APPLY_SUPPORTED, 'checks': checks}


def write_report(report, directory, inventory):
    directory = report_destination(directory, inventory)
    require(directory.is_absolute() and directory.resolve() == directory and directory.is_dir())
    if os.name == 'posix':
        info = directory.stat()
        require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) & 0o077 == 0)
    name = 'whatnot-preflight-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex + '.json'
    with os.fdopen(os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')
    return name


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise Blocker()


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('operation', choices=('preflight', 'deploy', 'rollback'))
    parser.add_argument('--inventory', required=True)
    parser.add_argument('--report-dir')
    parser.add_argument('--preflight-report')
    parser.add_argument('--apply', action='store_true')
    try:
        args = parser.parse_args(argv)
        if args.operation != 'preflight':
            # No report, flag, credential or inventory value can bypass this.
            # No human confirmation is requested for an unavailable operation.
            plan = DEPLOY_PLAN if args.operation == 'deploy' else ROLLBACK_PLAN
            try:
                require(args.preflight_report is not None)
                bound_report(args.inventory, args.preflight_report)
                report_gate = 'BOUND_FAIL_REPORT'
            except Exception:
                report_gate = 'INVALID_OR_MISSING'
            print(json.dumps({'operation': args.operation, 'mode': 'apply' if args.apply else 'dry-run',
                'status': 'BLOCKED', 'live_apply_supported': False,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'preflight_report': report_gate, 'steps_executed': False,
                'reason': 'reviewed_ec2_adapter_writer_barriers_and_compatible_rollback_required',
                'plan': plan}))
            return 2
        require(not args.apply and args.report_dir is not None and args.preflight_report is None)
        inventory = read_json(args.inventory)
        # An unsupported host must not probe a Windows/local application DB.
        require(platform.system() == 'Linux')
        checker = Preflight(inventory)
        report = checker.run()
        report['inventory_sha256'] = digest(args.inventory)
        filename = write_report(report, args.report_dir, inventory)
        print(json.dumps({'status': report['status'], 'report': filename, 'checks': report['checks']}))
        return 2
    except KeyboardInterrupt:
        print('{"status":"FAIL","reason":"interrupted_no_live_changes"}')
        return 130
    except Exception:
        print('{"status":"FAIL","reason":"invalid_or_unavailable_input_no_live_changes"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
