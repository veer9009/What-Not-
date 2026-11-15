"""Resume only tests after successful migration; no restore, upgrade or cleanup."""
import ast
from contextlib import redirect_stdout, redirect_stderr
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from rehearse_existing_server import (SOURCE,REHEARSAL,TESTS,ARCHIVE,ROOT,
    IDENTITY_SQL,verify_identity,Settings,make_url,psycopg,snapshot,require)
from sqlalchemy import create_engine,event
from sqlalchemy.engine import Engine
from sqlalchemy import text

STAGE = 'initialization'

def main():
    global STAGE
    STAGE = 'configuration'
    require(sys.argv[1:] in ([], ['--after-cutover'], ['--preparation'], ['--location'], ['--discovery']), 'Unknown test-run mode')
    investigation = sys.argv[1:] == ['--discovery']
    location = sys.argv[1:] == ['--location'] or investigation
    preparation = sys.argv[1:] == ['--preparation'] or location
    source=make_url(Settings().database_url.get_secret_value())
    require(source.database==SOURCE and source.host in {'localhost','127.0.0.1','::1'},'Source mismatch')
    def args(name):
        return dict(host=source.host,port=source.port or 5432,user=source.username,
            password=source.password,dbname=name,connect_timeout=5,
            options='-c default_transaction_read_only=on -c statement_timeout=30000')
    STAGE = 'read-only source snapshot'
    with psycopg.connect(**args(SOURCE)) as c:
        require(c.execute('SHOW transaction_read_only').fetchone()[0]=='on','Source read-only unavailable')
        before=snapshot(c)
        expected_revision='0008' if sys.argv[1:] == ['--after-cutover'] or preparation else '0004'
        require(before['alembic_version']==[({'version_num':expected_revision},)],'Source revision mismatch')
    STAGE = 'read-only target identity checks'
    for name,oid in [(REHEARSAL,49264),(TESTS,49265)]:
        with psycopg.connect(**args(name)) as c:
            verify_identity(c.execute(IDENTITY_SQL).fetchone(),name,oid)
            require(c.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0008','Target revision mismatch')
            if name==TESTS:
                initial_test_rows = snapshot(c)
                require(all(not rows for table,rows in initial_test_rows.items() if table not in {'alembic_version','request_quotas'}),
                    'Unexpected test business records before collection')
    checks=0
    def guard(connection,cursor,statement,parameters,context,executemany):
        nonlocal checks
        raw=connection.connection.driver_connection
        require(raw.info.dbname==TESTS,'Unexpected connected database')
        if raw.info.transaction_status==psycopg.pq.TransactionStatus.INERROR:
            # PostgreSQL forbids SELECT while aborted. Rollback cannot change the
            # database of this physical connection; allow only transaction recovery.
            require(statement.strip().upper().startswith('ROLLBACK TO SAVEPOINT '),
                    'Only savepoint recovery is allowed in an aborted transaction')
            checks+=1
            return
        with raw.cursor() as c:
            c.execute(IDENTITY_SQL)
            verify_identity(c.fetchone(),TESTS,49265)
        checks+=1
    event.listen(Engine,'before_cursor_execute',guard)
    engine=create_engine(source.set(database=TESTS),hide_parameters=True)
    try:
        # Only prior test quota counters survive the rollback-based fixtures.
        # Identity is checked by the listener immediately before this write.
        if not preparation:
            with engine.begin() as c:
                c.execute(text('DELETE FROM request_quotas'))
        STAGE = 'copy rollback-isolated test fixtures'
        folder=(Path(tempfile.mkdtemp(prefix='WhatNotLocationQA-')) if location
                else ARCHIVE.parent/('guarded-tests-'+str(time.time_ns())))
        shutil.copytree(ROOT/'backend/tests/persistence',folder,dirs_exist_ok=location,
                        ignore=shutil.ignore_patterns('__pycache__'))
        fixture=folder/'conftest.py'
        fixture_source=fixture.read_text()
        lines=fixture_source.splitlines(keepends=True)
        nodes=[n for n in ast.parse(fixture_source).body if isinstance(n,ast.FunctionDef) and n.name in
               {'migrated_engine','isolated_cluster','fresh_database_url'}]
        for n in sorted(nodes,key=lambda n:n.lineno,reverse=True):
            a=min([n.lineno]+[d.lineno for d in n.decorator_list])-1
            if n.name=='migrated_engine':
                replacement='@pytest.fixture(scope="session")\ndef migrated_engine():\n    from approved_test_engine import engine\n    yield engine\n'
            else:
                replacement=f'@pytest.fixture\ndef {n.name}():\n    pytest.fail("Server startup/database creation disabled")\n'
            lines[a:n.end_lineno]=[replacement]
        # Preserve the parent HTTP client fixture when relocating this directory.
        parent_fixture=(ROOT/'backend/tests/conftest.py').read_text()
        fixture.write_text(''.join(lines)+'\n'+parent_fixture,encoding='utf-8')
        import types
        module=types.ModuleType('approved_test_engine')
        module.engine=engine
        sys.modules['approved_test_engine']=module
        import pytest
        selected=['test_authentication.py','test_auth_transactions.py','test_beta_abuse.py',
            'test_authorization.py','test_constraints.py','test_order_creation.py',
            'test_discovery.py','test_security_audit.py','test_request_sessions.py']
        if preparation:
            # Preserve existing quota history and omit tests that deliberately
            # commit independent quota counters. All selected business fixtures
            # use rollback-isolated transactions on the guarded TESTS target.
            selected.remove('test_beta_abuse.py')
        extra_args = []
        if location:
            selected = ['test_discovery.py', 'test_order_geography.py', 'test_dispatch_location.py']
            if investigation:
                selected.append('test_beta_resume.py::test_http_discovery_probes_cannot_distinguish_private_points_in_one_cell')
            # This single historical migration test needs fresh databases and a
            # downgrade. It is outside location QA; creation fixtures remain disabled.
            extra_args = ['-k', 'not test_confirmation_migration_preserves_legacy_rows']
        log=folder/'pytest.log'
        xml=folder/'tests.xml'
        STAGE = 'guarded pytest execution'
        with log.open('w',encoding='utf-8') as out,redirect_stdout(out),redirect_stderr(out):
            code=pytest.main(['--assert=plain','-q','-x','-W','error',
                '-c',str(ROOT/'backend/pytest.ini'),'--junitxml='+str(xml),
                *extra_args, *[str(folder/f) for f in selected]])
        import xml.etree.ElementTree as ET
        root=ET.parse(xml).getroot()
        suite=root.find('testsuite')
        result={'exit_code':int(code),'database':TESTS,'oid':49265,
            'tests':int(suite.attrib['tests']),'failures':int(suite.attrib['failures']),
            'errors':int(suite.attrib['errors']),'skipped':int(suite.attrib['skipped']),
            'seconds':suite.attrib['time'],'guarded_sql_statements':checks,'log':str(log)}
        STAGE = 'read-only post-test snapshots'
        with psycopg.connect(**args(SOURCE)) as c:
            require(snapshot(c)==before,'Original records changed during tests')
        result['original_rows_unchanged']=True
        if preparation:
            with psycopg.connect(**args(TESTS)) as c:
                verify_identity(c.execute(IDENTITY_SQL).fetchone(),TESTS,49265)
                require(snapshot(c)==initial_test_rows,'Isolated test records changed; no cleanup attempted')
            result['isolated_test_rows_unchanged'] = True
        result['quota_cleanup_performed'] = not preparation
        evidence_name = 'production-preparation-database-tests.json' if preparation else 'auth-database-tests.json'
        if location:
            evidence_name = 'live-location-database-tests.json'
        if investigation:
            evidence_name = 'discovery-investigation-database-tests.json'
        STAGE = 'write sanitized test evidence'
        (Path(__file__).parent/'evidence'/evidence_name).write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2),flush=True)
        require(code==0,'Database tests failed; inspect protected log')
        return 0
    finally:
        engine.dispose()
        event.remove(Engine,'before_cursor_execute',guard)


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,
            'stage':STAGE,
            'blocked_filename':Path(error.filename).name if isinstance(error,PermissionError) and error.filename else None,
            'message':str(error) if type(error) is RuntimeError else 'Private inputs suppressed'}),flush=True)
        raise SystemExit(1)
