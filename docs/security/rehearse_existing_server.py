"""Pinned existing-server rehearsal; no CREATE/DROP DATABASE or server startup."""
import ast
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rehearse_auth_recovery import snapshot, require, Settings, make_url, psycopg
from recovery_validation import validate_copy, smoke_authentication
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

ROOT = HERE.parents[1]
SOURCE = 'whatnot_app_dev'
REHEARSAL = 'whatnot_rehearsal_20261115_a7e394c2'
TESTS = 'whatnot_tests_20261115_a7e394c2'
ARCHIVE = Path(r'C:\Users\DELL\AppData\Local\Temp\WhatNotRecovery-321h5wu2\original-0004.dump')
CHECKSUM = '4e3ea42158673f1ee355150b083e41bd72f35ffd1d39006073e4a15d8135708b'
IDENTITY_SQL = """SELECT current_database(),oid,datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user)
    FROM pg_database WHERE datname=current_database()"""
TEST_ENGINE = None


def verify_identity(actual, name, oid):
    require(name in {REHEARSAL, TESTS} and name != SOURCE,
            'Unapproved write target')
    require(tuple(actual) == (name, oid, True), 'Database name/OID/owner mismatch')


def main():
    require(not sys.argv[1:], 'Restore runner accepts no resume flags; use run_existing_server_tests.py')
    source = make_url(Settings().database_url.get_secret_value())
    require(source.database == SOURCE and source.host in {'localhost','127.0.0.1','::1'},
            'Unexpected source configuration')
    folder = ARCHIVE.parent
    evidence = {'date':'2026-11-15', 'stages':{}, 'source_writes_permitted':False}
    evidence_path = HERE / 'evidence/auth-rehearsal-final.json'
    stage = 'preflight'
    oids = {}
    statements_checked = 0

    def save(label, value):
        evidence['stages'][label] = value
        evidence_path.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        (folder/'existing-server-evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        print(json.dumps({'stage':label,**value}),flush=True)

    def args(name, readonly=True):
        return dict(host=source.host,port=source.port or 5432,user=source.username,
            password=source.password,dbname=name,connect_timeout=5,
            options='-c default_transaction_read_only='+('on' if readonly else 'off')+' -c lock_timeout=5000 -c statement_timeout=30000')

    def identity(connection, name):
        actual = connection.execute(IDENTITY_SQL).fetchone()
        verify_identity(actual,name,oids[name])

    def sql_guard(connection,cursor,statement,parameters,context,executemany):
        nonlocal statements_checked
        raw = connection.connection.driver_connection
        with raw.cursor() as check:
            check.execute(IDENTITY_SQL)
            actual = check.fetchone()
        require(actual[0] in oids, 'SQL attempted outside approved databases')
        verify_identity(actual,actual[0],oids[actual[0]])
        statements_checked += 1

    def config(name):
        require(name in oids, 'Unverified migration target')
        c = Config(str(ROOT/'backend/alembic.ini'))
        c.attributes['database_url'] = source.set(database=name)
        return c

    try:
        with psycopg.connect(**args(SOURCE)) as original:
            require(original.execute('SHOW transaction_read_only').fetchone()[0]=='on','Source not read only')
            original.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            require(original.execute('SELECT current_database()').fetchone()[0]==SOURCE,'Wrong source')
            baseline = snapshot(original)
            require(baseline['alembic_version']==[({'version_num':'0004'},)],'Source revision changed')
            require(len(baseline['users'])==5 and len(baseline['orders'])==3,'Source counts changed')
            for name in (REHEARSAL,TESTS):
                row = original.execute('SELECT oid,datdba=(SELECT datdba FROM pg_database WHERE datname=%s) FROM pg_database WHERE datname=%s',(SOURCE,name)).fetchone()
                require(row is not None and row[1], 'Missing target or owner differs from original')
                oids[name] = row[0]
                with psycopg.connect(**args(name)) as target:
                    identity(target,name)
                    objects = target.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_%'").fetchone()[0]
                    require(objects==0,'Target is not empty; refusing restore or test initialization')
            require(len(set(oids.values()))==2,'Target OIDs overlap')
        save(stage,{'status':'PASS','source_revision':'0004','source_users':5,'source_orders':3,
            'empty_verified_targets':oids,'owner_matches':True})
        stage = 'backup'
        require(hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==CHECKSUM,'Backup checksum mismatch')
        pg_restore = shutil.which('pg_restore')
        psql = shutil.which('psql')
        require(pg_restore and psql,'Restore clients unavailable')
        listing = subprocess.run([pg_restore,'--list',str(ARCHIVE)],capture_output=True,text=True)
        require(listing.returncode==0 and 'TABLE DATA' in listing.stdout,'Unreadable archive')
        save(stage,{'status':'PASS','archive':str(ARCHIVE),'bytes':ARCHIVE.stat().st_size,
            'sha256':CHECKSUM,'pg_restore_list_exit':listing.returncode})
        stage = 'restore'
        sql_path = folder/'existing-server-restore.sql'
        generated = subprocess.run([pg_restore,'--no-owner','--no-privileges','--file',str(sql_path),str(ARCHIVE)],capture_output=True)
        require(generated.returncode==0,'Archive SQL extraction failed')
        guard_path = folder/'existing-server-target-guard.sql'
        guard_path.write_text(f"""DO $guard$ BEGIN
          IF current_database() <> '{REHEARSAL}' OR
            (SELECT oid FROM pg_database WHERE datname=current_database()) <> {oids[REHEARSAL]} OR
            NOT (SELECT datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user) FROM pg_database WHERE datname=current_database())
          THEN RAISE EXCEPTION 'Restore target identity mismatch'; END IF;
        END; $guard$;\n""",encoding='utf-8')
        with psycopg.connect(**args(REHEARSAL)) as target:
            identity(target,REHEARSAL)
            require(not snapshot(target),'Restore target is no longer empty')
        env = {k:v for k,v in os.environ.items() if not k.upper().startswith('PG')}
        env.update(PGPASSWORD=source.password or '', PGOPTIONS='-c lock_timeout=5000 -c statement_timeout=30000')
        with (folder/'existing-server-restore.log').open('wb') as log:
            result = subprocess.run([psql,'--no-psqlrc','--no-password','--host',source.host,
                '--port',str(source.port or 5432),'--username',source.username,'--dbname',REHEARSAL,
                '--set','ON_ERROR_STOP=1','--single-transaction','--file',str(guard_path),
                '--file',str(sql_path)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        require(result.returncode==0,'Transactional restore failed; inspect protected log')
        with psycopg.connect(**args(REHEARSAL)) as target:
            identity(target,REHEARSAL)
            restored = snapshot(target)
            require(restored==baseline,'Restored records differ from read-only source baseline')
        save(stage,{'status':'PASS','psql_restore_exit':result.returncode,'restored_revision':'0004',
            'all_original_rows_match':True,'counts':{t:len(r) for t,r in restored.items()}})
        event.listen(Engine,'before_cursor_execute',sql_guard)
        stage = 'migration'
        with psycopg.connect(**args(REHEARSAL)) as target:
            identity(target,REHEARSAL)
        start = time.monotonic()
        command.upgrade(config(REHEARSAL),'0008')
        save(stage,{'status':'PASS','target':REHEARSAL,'revision':'0008',
                    'elapsed_seconds':round(time.monotonic()-start,3)})
        stage = 'validation'
        validate_copy(source.set(database=REHEARSAL),baseline,config(REHEARSAL),args(REHEARSAL),save)
        stage = 'authentication_smoke'
        smoke_authentication(source.set(database=REHEARSAL),args(REHEARSAL),save)
        stage = 'database_tests'
        with psycopg.connect(**args(TESTS)) as target:
            identity(target,TESTS)
            require(not snapshot(target),'Test database is no longer empty')
        command.upgrade(config(TESTS),'0008')
        global TEST_ENGINE
        TEST_ENGINE = create_engine(source.set(database=TESTS),hide_parameters=True)
        sys.modules['rehearse_existing_server'] = sys.modules[__name__]
        test_dir = folder/'guarded-persistence-tests'
        require(not test_dir.exists(),'Temporary tests already exist')
        shutil.copytree(ROOT/'backend/tests/persistence',test_dir,
                        ignore=shutil.ignore_patterns('__pycache__'))
        fixture_path = test_dir/'conftest.py'
        fixture_source = fixture_path.read_text()
        tree = ast.parse(fixture_source)
        replacements=[]
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name in {'migrated_engine','isolated_cluster','fresh_database_url'}:
                start_line = min([node.lineno]+[d.lineno for d in node.decorator_list])-1
                if node.name=='migrated_engine':
                    replacement='@pytest.fixture(scope="session")\ndef migrated_engine():\n    from rehearse_existing_server import TEST_ENGINE\n    yield TEST_ENGINE\n'
                else:
                    replacement=f'@pytest.fixture\ndef {node.name}():\n    pytest.fail("Cluster/database creation disabled in approved existing-server test run")\n'
                replacements.append((start_line,node.end_lineno,replacement))
        lines=fixture_source.splitlines(keepends=True)
        for start_line,end_line,replacement in sorted(replacements,reverse=True):
            lines[start_line:end_line]=[replacement]
        fixture_path.write_text(''.join(lines),encoding='utf-8')
        files=['test_authentication.py','test_auth_transactions.py','test_beta_abuse.py',
               'test_authorization.py','test_constraints.py','test_order_creation.py',
               'test_discovery.py','test_security_audit.py','test_request_sessions.py']
        import pytest
        test_log = folder/'existing-server-pytest.log'
        with test_log.open('w',encoding='utf-8') as log, redirect_stdout(log),redirect_stderr(log):
            exit_code = pytest.main(['-q','-x','-W','error','-c',str(ROOT/'backend/pytest.ini'),
                '--junitxml='+str(folder/'existing-server-tests.xml'),
                *[str(test_dir/f) for f in files]])
        TEST_ENGINE.dispose()
        require(exit_code==0,'Database tests failed; inspect protected pytest log')
        import xml.etree.ElementTree as ET
        suite=ET.parse(folder/'existing-server-tests.xml').getroot().find('testsuite')
        save(stage,{'status':'PASS','exit_code':int(exit_code),'tests':int(suite.attrib['tests']),
            'failures':int(suite.attrib['failures']),'errors':int(suite.attrib['errors']),
            'log':str(test_log),'target':TESTS,'source_tests_unchanged':True})
        stage = 'original_unchanged'
        with psycopg.connect(**args(SOURCE)) as original:
            require(original.execute('SHOW transaction_read_only').fetchone()[0]=='on','Source read-only lost')
            require(snapshot(original)==baseline,'Original records changed during rehearsal')
        save(stage,{'status':'PASS','revision':'0004','all_original_rows_unchanged':True,
                    'guarded_sql_statements':statements_checked})
        return 0
    except Exception as error:
        save(stage,{'status':'FAIL','exception_class':type(error).__name__,
            'message':str(error) if type(error) is RuntimeError else 'Stopped; private exception inputs suppressed'})
        return 1
    finally:
        if event.contains(Engine,'before_cursor_execute',sql_guard):
            event.remove(Engine,'before_cursor_execute',sql_guard)


if __name__=='__main__':
    raise SystemExit(main())
