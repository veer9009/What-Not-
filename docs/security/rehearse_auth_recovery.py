"""Approved local recovery rehearsal. Never migrate or write the source database.

Run once from the repository root with the backend virtual environment. Archives,
private PostgreSQL logs and restored data are retained in an ACL-restricted TEMP
directory outside OneDrive. Any failed stage stops progression. No cleanup drops.
"""
import hashlib
import json
import logging
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

import psycopg
from psycopg import sql
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models import User
from app.models.abuse import RequestQuota
from app.repositories.users import UserRepository


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def assess_source_sessions(rows):
    """Classify observations, without claiming future writers are excluded.

    Rows contain state, open-transaction flag, business-table lock flag, count.
    Never inspect or return query text, client identities or credentials.
    """
    ordinary = 0
    risks = []
    for state, transaction, write_lock, count in rows:
        if state == 'idle' and not transaction and not write_lock:
            ordinary += count
        else:
            risks.append({'state': state or 'unobservable', 'open_transaction': transaction,
                          'potential_write_lock': write_lock, 'count': count})
    return {'safe_to_snapshot': not risks, 'ordinary_idle_sessions': ordinary,
            'risk_session_count': sum(r['count'] for r in risks),
            'risks': risks, 'future_writes_excluded': False}


def snapshot(connection):
    """Private in-memory row comparison; never serialize customer records."""
    tables = [r[0] for r in connection.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
    return {table: connection.execute(sql.SQL(
        'SELECT to_jsonb(t) FROM public.{} t ORDER BY to_jsonb(t)::text'
    ).format(sql.Identifier(table))).fetchall() for table in tables}


def main():
    settings = Settings()
    require(settings.database_url is not None, 'Missing database configuration')
    source = make_url(settings.database_url.get_secret_value())
    require(source.host in {'localhost', '127.0.0.1', '::1'}, 'Refusing nonlocal source')
    binaries = {name: shutil.which(name) for name in
                ('pg_dump', 'pg_restore', 'initdb', 'pg_ctl')}
    require(all(binaries.values()), 'Required PostgreSQL binaries unavailable')
    recovery = Path(tempfile.mkdtemp(prefix='WhatNotRecovery-')).resolve()
    require(ROOT not in recovery.parents, 'Backup must be outside source workspace')
    identity = subprocess.check_output(['whoami'], text=True).strip()
    acl = subprocess.run(['icacls', str(recovery), '/inheritance:r', '/grant:r',
                          f'{identity}:(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'],
                         capture_output=True, text=True)
    require(acl.returncode == 0, 'Could not restrict backup directory permissions')
    evidence = {'recovery_directory': str(recovery), 'stages': {},
                'original_database_writes_authorized': False}
    report = recovery / 'rehearsal-evidence.json'
    stage = 'preflight'
    started = False
    target = None

    def save(name, value):
        evidence['stages'][name] = value
        report.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        print(json.dumps({'stage': name, **value}), flush=True)

    # Do not inherit PG* service/connection settings into subprocesses.
    clean_env = {k: v for k, v in os.environ.items() if not k.upper().startswith('PG')}

    def run(binary, args, env=None, timeout=180):
        log = recovery / (binary + '-' + str(time.time_ns()) + '.log')
        with log.open('wb') as stream:
            completed = subprocess.run([binaries[binary], *map(str, args)],
                env=env or clean_env, stdout=stream, stderr=subprocess.STDOUT,
                timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
        require(completed.returncode == 0, f'{binary} failed; inspect protected log')
        return log

    source_args = dict(host=source.host, port=source.port or 5432,
        user=source.username, password=source.password, dbname=source.database,
        connect_timeout=5, application_name='whatnot_recovery_readonly',
        options='-c default_transaction_read_only=on -c statement_timeout=10000 -c lock_timeout=2000')
    try:
        with psycopg.connect(**source_args) as original:
            original.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            require(original.execute('SHOW transaction_read_only').fetchone()[0] == 'on',
                    'Original read-only enforcement failed')
            dbname, version, port = original.execute(
                'SELECT current_database(), current_setting(\'server_version\'), inet_server_port()').fetchone()
            require(dbname == source.database, 'Source database identity mismatch')
            baseline = snapshot(original)
            require(baseline['alembic_version'] == [({'version_num': '0004'},)],
                    'Source revision is not the approved 0004')
            users = baseline['users']
            orders = {r[0]['id']: r[0] for r in baseline['orders']}
            status_counts = {}
            for row in orders.values():
                status_counts[row['status']] = status_counts.get(row['status'], 0) + 1
            require(len(users) == 5 and status_counts == {'DELIVERED': 2, 'PLACED': 1},
                    'Source data differs from approved incident snapshot')
            session_rows = original.execute("""WITH observations AS (
                SELECT state, xact_start IS NOT NULL AS open_transaction,
                EXISTS(SELECT 1 FROM pg_locks l JOIN pg_class c ON c.oid=l.relation
                  JOIN pg_namespace n ON n.oid=c.relnamespace
                  WHERE l.pid=a.pid AND l.database=(SELECT oid FROM pg_database WHERE datname=current_database())
                    AND n.nspname='public' AND l.granted
                    AND l.mode IN ('RowShareLock','RowExclusiveLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock')) AS potential_write_lock
                FROM pg_stat_activity a
                WHERE datname=current_database() AND pid<>pg_backend_pid())
                SELECT state,open_transaction,potential_write_lock,count(*) FROM observations
                GROUP BY state,open_transaction,potential_write_lock""").fetchall()
            session_assessment = assess_source_sessions(session_rows)
            prepared = original.execute('SELECT count(*) FROM pg_prepared_xacts WHERE database=current_database()').fetchone()[0]
            save('source_session_observation', {**session_assessment,
                 'prepared_transactions': prepared,
                 'consistency_strategy': 'Exported REPEATABLE READ snapshot, not assumed writer quiescence'})
            require(session_assessment['safe_to_snapshot'] and prepared == 0,
                    'Source transaction or potential-write risk requires review')
            owner_match = original.execute("SELECT count(*) FILTER (WHERE pg_get_userbyid(relowner)<>current_user) FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname='public' AND c.relkind IN ('r','S')").fetchone()[0] == 0
            save(stage, {'status': 'PASS', 'database': dbname, 'host': 'loopback',
                'port': port, 'server_version': version, 'revision': '0004',
                'users': len(users), 'orders': status_counts,
                'session_observation': session_assessment,
                'all_public_tables_sequences_owned_by_configured_role': owner_match,
                'transaction_read_only': True, 'protected_directory': str(recovery)})
            stage = 'backup'
            archive = recovery / 'original-0004.dump'
            dump_env = dict(clean_env, PGPASSWORD=source.password or '',
                PGOPTIONS='-c default_transaction_read_only=on -c lock_timeout=5000',
                PGAPPNAME='whatnot_recovery_dump')
            snapshot_id = original.execute('SELECT pg_export_snapshot()').fetchone()[0]
            require(bool(snapshot_id), 'Consistent snapshot export failed')
            run('pg_dump', ['--host', source.host, '--port', str(source.port or 5432),
                '--username', source.username, '--dbname', source.database, '--no-password',
                '--format=custom', '--snapshot', snapshot_id, '--file', archive], dump_env)
            toc = run('pg_restore', ['--list', archive])
            require(archive.stat().st_size > 0 and 'TABLE DATA' in toc.read_text(),
                    'Archive listing did not contain table data')
            checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
            (recovery / 'original-0004.dump.sha256').write_text(checksum+'  original-0004.dump\n', encoding='ascii')
            require(hashlib.sha256(archive.read_bytes()).hexdigest() == checksum,
                    'Backup checksum verification failed')
            save(stage, {'status': 'PASS', 'path': str(archive), 'bytes': archive.stat().st_size,
                'sha256': checksum, 'checksum_verified': True,
                'pg_dump_exit': 0, 'pg_restore_list_exit': 0,
                'consistent_exported_snapshot': True, 'includes_database_acl_and_owners': True,
                'cluster_roles_and_tablespaces_included': False})
        stage = 'restore'
        data = recovery / 'rehearsal-data'
        clone_password = secrets.token_urlsafe(40)
        password_file = recovery / 'initial-password'
        password_file.write_text(clone_password, encoding='utf-8')
        run('initdb', ['-D', data, '-U', 'whatnot_rehearsal', '--auth=scram-sha-256',
            '--pwfile', password_file, '--encoding=UTF8', '--no-locale',
            '-c', 'max_connections=20', '-c', 'shared_buffers=16MB'], timeout=600)
        password_file.unlink()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            clone_port = sock.getsockname()[1]
        require(clone_port != (source.port or 5432), 'Clone port equals source port')
        started = True
        run('pg_ctl', ['-D', data, '-l', recovery / 'rehearsal-server.log', '-w', '-t', '45',
            '-o', f'-h 127.0.0.1 -p {clone_port}', 'start'])
        target = URL.create('postgresql+psycopg', username='whatnot_rehearsal',
            password=clone_password, host='127.0.0.1', port=clone_port,
            database='whatnot_auth_rehearsal')
        clone_args = dict(host=target.host, port=clone_port, user=target.username,
                          password=clone_password, dbname='postgres', connect_timeout=5)
        with psycopg.connect(**clone_args, autocommit=True) as admin:
            require(Path(admin.execute('SHOW data_directory').fetchone()[0]).resolve() == data,
                    'Wrong rehearsal cluster identity')
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target.database)))
        clone_args['dbname'] = target.database
        clone_env = dict(clean_env, PGPASSWORD=clone_password)
        require(hashlib.sha256(archive.read_bytes()).hexdigest() == checksum,
                'Backup checksum changed before restore')
        run('pg_restore', ['--host', target.host, '--port', str(clone_port),
            '--username', target.username, '--dbname', target.database, '--no-password',
            '--exit-on-error', '--single-transaction', '--no-owner', '--no-privileges', archive], clone_env)
        with psycopg.connect(**clone_args) as restored:
            require(snapshot(restored) == baseline, 'Restored original rows do not match snapshot')
        save(stage, {'status': 'PASS', 'pg_restore_exit': 0, 'exact_all_original_table_rows': True,
            'users_preserved': len(users), 'orders_preserved': len(orders),
            'restored_record_counts': {table:len(rows) for table,rows in baseline.items()},
            'database': target.database, 'port': clone_port,
            'separate_cluster_verified': True, 'data_directory': str(data),
            'rehearsal_ownership_acl': 'Remapped to isolated role; original ACLs retained in archive'})
        stage = 'migration'
        require(target.database != source.database and target.port != (source.port or 5432),
                'Rehearsal target isolation lost')
        config = Config(str(ROOT / 'backend/alembic.ini'))
        config.attributes['database_url'] = target
        start = time.monotonic()
        command.upgrade(config, '0008')
        save(stage, {'status': 'PASS', 'target_revision': '0008',
                     'elapsed_seconds': round(time.monotonic()-start, 3)})
        stage = 'validation'
        engine = create_engine(target, echo=False, hide_parameters=True)
        try:
            with psycopg.connect(**clone_args) as clone:
                current = snapshot(clone)
                require(current['alembic_version'] == [({'version_num': '0008'},)], 'Wrong final revision')
                for table, rows in baseline.items():
                    if table not in {'alembic_version', 'users', 'orders'}:
                        require(current[table] == rows, 'Original business rows changed unexpectedly')
                preserved = [{k:v for k,v in r[0].items() if k not in
                    {'phone_verified_at','email_verified_at'}} for r in current['users']]
                require(sorted(preserved, key=lambda r:r['id']) == sorted(
                    [r[0] for r in users], key=lambda r:r['id']), 'Original user fields changed')
                require(all(r[0]['phone_verified_at'] is None and r[0]['email_verified_at'] is None
                            for r in current['users']), 'Unexpected verification evidence')
                audits = [r[0] for r in current['audit_events']]
                require(len(audits) == 2, 'Unexpected migration audit count')
                converted = 0
                for row, in current['orders']:
                    previous = orders[row['id']]
                    expected = dict(previous)
                    expected.update(delivered_at=None, confirmation_deadline=None,
                                    completed_at=None, completion_source=None)
                    if previous['status'] == 'DELIVERED':
                        expected.update(status='COMPLETED', completion_source='LEGACY')
                        converted += 1
                        matching = [a for a in audits if a['entity_id'] == row['id'] and
                            a['actor_type']=='MIGRATION' and a['entity_type']=='order' and
                            a['action']=='ORDER_MIGRATION' and a['previous_status']=='DELIVERED' and
                            a['next_status']=='COMPLETED' and a['reason']=='0005_LEGACY_MAPPING']
                        require(len(matching) == 1, 'Missing exact order migration audit event')
                    require(row == expected, 'Order transformation mismatch')
                invalid = clone.execute("SELECT count(*) FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated").fetchone()[0]
                invalid_indexes = clone.execute("SELECT count(*) FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND (NOT i.indisvalid OR NOT i.indisready)").fetchone()[0]
                require(invalid == 0 and invalid_indexes == 0, 'Invalid constraints or indexes')
                sequences = clone.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public' AND column_default LIKE 'nextval(%'").fetchall()
                for table, column in sequences:
                    seq = clone.execute('SELECT pg_get_serial_sequence(%s,%s)', (f'public.{table}',column)).fetchone()[0]
                    last, called = clone.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(*seq.split('.')))).fetchone()
                    maximum = clone.execute(sql.SQL('SELECT max({}) FROM public.{}').format(sql.Identifier(column),sql.Identifier(table))).fetchone()[0]
                    require(maximum is None or last > maximum or (called and last == maximum), 'Sequence behind existing IDs')
            with engine.connect() as connection:
                inspector = inspect(connection)
                for table in Base.metadata.sorted_tables:
                    require(inspector.has_table(table.name), 'Missing ORM table')
                    require(set(table.columns.keys()) <= {c['name'] for c in inspector.get_columns(table.name)}, 'Missing ORM columns')
                connection.execute(select(User).limit(0))
                connection.execute(select(RequestQuota).limit(0))
            with Session(engine) as session:
                require(len(UserRepository(session).by_normalized_email(users[0][0]['email'].lower())) == 1,
                        'Existing-user authentication lookup failed')
            command.check(config)
            save(stage, {'status':'PASS', 'original_users_unchanged':5,
                'legacy_order_conversions':converted, 'placed_orders_unchanged':1,
                'matching_migration_audit_events':len(audits), 'all_original_other_rows_unchanged':True,
                'orm_table_column_coverage':True, 'alembic_check':'PASS',
                'request_quotas_table_present':True, 'user_verification_columns_present':True,
                'invalid_constraints':invalid, 'invalid_indexes':invalid_indexes,
                'sequences_checked':len(sequences), 'auth_queries':'PASS'})
        finally:
            engine.dispose()
        stage = 'authentication_smoke'
        # Explicit clone URL, new ephemeral signing key, no SMTP and no workers.
        smoke_settings = Settings(_env_file=None, database_url=target.render_as_string(hide_password=False),
            environment='development', jwt_secret_key=secrets.token_urlsafe(48),
            email_provider='disabled', beta_allowed_emails=[], abuse_limits_enabled=True)
        require(make_url(smoke_settings.database_url.get_secret_value()) == target, 'Smoke DB mismatch')
        application = create_app(smoke_settings)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        password = secrets.token_urlsafe(32)
        payload = dict(name='Recovery rehearsal buyer', email='recovery-rehearsal@example.com',
                       phone='rehearsal-'+secrets.token_hex(6), password=password, role='BUYER')
        statuses = {}
        with TestClient(application) as client:
            def check(label, method, path, expected, **kwargs):
                response = client.request(method, '/api/v1'+path, **kwargs)
                statuses[label] = response.status_code
                require(response.status_code == expected, f'{label} HTTP status mismatch')
                return response
            check('readiness','GET','/ready',200)
            registration = check('registration','POST','/auth/register',201,json=payload)
            check('duplicate_registration','POST','/auth/register',409,json=payload)
            check('invalid_registration','POST','/auth/register',422,json={})
            login = check('login','POST','/auth/login',200,json=dict(email=payload['email'],password=password))
            me = check('authenticated_identity','GET','/auth/me',200,
                       headers={'Authorization':'Bearer '+login.json()['access_token']})
            require(me.json()['id'] == registration.json()['id'], 'Authenticated identity mismatch')
            check('wrong_password','POST','/auth/login',401,json=dict(email=payload['email'],password='wrong-password'))
            check('invalid_token','GET','/auth/me',401,headers={'Authorization':'Bearer invalid'})
        with psycopg.connect(**clone_args) as clone:
            quotas = clone.execute('SELECT count(*) FROM request_quotas').fetchone()[0]
            require(quotas > 0, 'Development authentication quotas were not written')
        save(stage, {'status':'PASS','http_statuses':statuses,'quota_rows_created':quotas,
                     'credentials_and_tokens_printed':False,'smtp_and_workers_disabled':True})
        stage = 'original_unchanged'
        with psycopg.connect(**source_args) as original:
            require(snapshot(original) == baseline, 'Original changed during rehearsal; stop for review')
        save(stage, {'status':'PASS','all_original_table_rows_match_before_backup':True,'revision':'0004'})
    except Exception as error:
        # Avoid raw SQLAlchemy / configuration exceptions containing private inputs.
        save(stage, {'status':'FAIL','exception_class':type(error).__name__,
             'sqlstate':getattr(error,'sqlstate',None),
             'message':str(error) if type(error) is RuntimeError else 'Stopped; inspect protected local evidence'})
        return 1
    finally:
        if started:
            try:
                run('pg_ctl', ['-D', recovery/'rehearsal-data', '-w', '-t', '45', '-m', 'fast', 'stop'])
                save('rehearsal_shutdown', {'status':'PASS','data_retained':True})
            except Exception:
                save('rehearsal_shutdown', {'status':'FAIL','data_retained':True})
                return 1
    print(json.dumps({'result':'REHEARSAL_PASS','evidence_path':str(report)}), flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'result':'STOP','exception_class':type(error).__name__}),flush=True)
        raise SystemExit(1)
