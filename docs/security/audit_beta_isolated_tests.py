"""Release-audit persistence runner, exclusively on disposable isolated test data.

DO NOT EXECUTE without separate permission for test-schema initialization.
The first audit run exceeded the no-migrations instruction; see the audit report.
Default execution now refuses before configuration/database access.

Uses a new schema on the existing empty test database, not Chrome QA. Never
connects to the original/rehearsal databases. Retains synthetic test schema/logs.
Tests needing additional databases are explicitly skipped; no pg_ctl is invoked.
"""
import ast
from contextlib import redirect_stdout, redirect_stderr
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import psycopg
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine, make_url
from alembic import command
from alembic.config import Config
from app.core.config import Settings

TEST_DATABASE = 'whatnot_tests_20261115_a7e394c2'
TEST_OID = 49265
IDENTITY = """SELECT current_database(),oid::bigint,
    datdba=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user),
    host(inet_server_addr()),inet_server_port()
    FROM pg_catalog.pg_database WHERE datname=current_database()"""


def require(value):
    if not value:
        raise RuntimeError('Isolated test safeguard failed')


def main():
    if sys.argv[1:] != ['--execute-test-schema-after-approval']:
        print('REFUSED: separate explicit owner approval for test-schema initialization '
              'is required. No database connection or migration executed.', flush=True)
        return 2
    base = make_url(Settings().database_url.get_secret_value())
    require(base.database == 'whatnot_app_dev' and base.host in {'localhost','127.0.0.1','::1'}
            and (base.port or 5432) == 5432 and not base.query)
    args = dict(host='127.0.0.1', port=5432, user=base.username, password=base.password,
                dbname=TEST_DATABASE, connect_timeout=5)
    with psycopg.connect(**args, options='-c default_transaction_read_only=on -c statement_timeout=5000') as c:
        require(c.execute(IDENTITY).fetchone() == (TEST_DATABASE, TEST_OID, True, '127.0.0.1', 5432))
        require(c.execute('SHOW transaction_read_only').fetchone()[0] == 'on')
        require(c.execute('SELECT version_num FROM public.alembic_version').fetchall() == [('0008',)])
        for table in ('users','seller_profiles','products','addresses','orders'):
            require(c.execute('SELECT count(*) FROM public.' + table).fetchone()[0] == 0)
        baseline = c.execute("""SELECT tablename FROM pg_catalog.pg_tables
            WHERE schemaname='public' ORDER BY tablename""").fetchall()
    schema = 'whatnot_audit_' + uuid4().hex
    url = base.set(host='127.0.0.1', database=TEST_DATABASE,
                   query={'options': '-csearch_path=' + schema + ' -clock_timeout=5000 -cstatement_timeout=30000'})
    checks = 0

    def guard(connection, cursor, statement, parameters, context, executemany):
        nonlocal checks
        raw = connection.connection.driver_connection
        require(raw.info.dbname == TEST_DATABASE)
        if raw.info.transaction_status == psycopg.pq.TransactionStatus.INERROR:
            require(statement.strip().upper().startswith('ROLLBACK TO SAVEPOINT '))
            return
        with raw.cursor() as check:
            check.execute(IDENTITY)
            require(check.fetchone() == (TEST_DATABASE, TEST_OID, True, '127.0.0.1', 5432))
            check.execute("SELECT current_setting('search_path')")
            require(check.fetchone()[0] == schema)
        checks += 1

    event.listen(Engine, 'before_cursor_execute', guard)
    engine = create_engine(url, hide_parameters=True)
    folder = Path(tempfile.mkdtemp(prefix='WhatNotFinalAudit-'))
    print('Verified isolated test identity; original/QA connections prohibited.', flush=True)
    try:
        with engine.begin() as c:
            # Identifier generated internally; never reuse any pre-existing schema.
            require(c.scalar(text('SELECT count(*) FROM pg_catalog.pg_namespace WHERE nspname=:name'),
                             {'name':schema}) == 0)
            c.execute(text('CREATE SCHEMA ' + schema))
        config = Config(str(ROOT / 'backend/alembic.ini'))
        with engine.begin() as c:
            config.attributes['connection'] = c
            command.upgrade(config, '0009')
        with engine.connect() as c:
            require(c.scalar(text('SELECT current_schema()')) == schema)
            require(c.scalar(text('SELECT version_num FROM alembic_version')) == '0009')
        print('Fresh test schema migrated 0001 -> 0009; starting persistence tests.', flush=True)
        shutil.copytree(ROOT / 'backend/tests/persistence', folder, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__'))
        fixture = folder / 'conftest.py'
        source = fixture.read_text(encoding='utf-8')
        lines = source.splitlines(keepends=True)
        functions = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
                     and n.name in {'isolated_cluster','fresh_database_url','migrated_engine'}]
        for n in sorted(functions, key=lambda n:n.lineno, reverse=True):
            start = min([n.lineno]+[d.lineno for d in n.decorator_list])-1
            if n.name == 'migrated_engine':
                replacement = '@pytest.fixture(scope="session")\ndef migrated_engine():\n    from beta_audit_test_engine import engine\n    yield engine\n'
            else:
                replacement = ('@pytest.fixture\ndef '+n.name+'():\n    pytest.skip("Requires a separate disposable database/cluster; CREATEDB unavailable; no original/QA fallback")\n')
            lines[start:n.end_lineno] = [replacement]
        fixture.write_text(''.join(lines)+'\n'+(ROOT/'backend/tests/conftest.py').read_text(), encoding='utf-8')
        module = types.ModuleType('beta_audit_test_engine')
        module.engine = engine
        sys.modules['beta_audit_test_engine'] = module
        import pytest
        with (folder/'pytest.log').open('w',encoding='utf-8') as output, redirect_stdout(output), redirect_stderr(output):
            code = pytest.main(['--assert=plain','-q','-W','error','-c',str(ROOT/'backend/pytest.ini'),
                                '--junitxml='+str(folder/'tests.xml'), str(folder)])
        import xml.etree.ElementTree as ET
        suite = ET.parse(folder/'tests.xml').getroot().find('testsuite')
        with engine.connect() as c:
            require(c.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' ORDER BY tablename")).fetchall() == baseline)
            require(c.scalar(text('SELECT version_num FROM public.alembic_version')) == '0008')
            for table in ('users','seller_profiles','products','addresses','orders'):
                require(c.scalar(text('SELECT count(*) FROM public.'+table)) == 0)
        result = dict(database=TEST_DATABASE,oid=TEST_OID,schema=schema,revision='0009',
            exit_code=int(code),tests=int(suite.attrib['tests']),failures=int(suite.attrib['failures']),
            errors=int(suite.attrib['errors']),skipped=int(suite.attrib['skipped']),
            seconds=suite.attrib['time'],guarded_sql_statements=checks,log=str(folder/'pytest.log'),
            public_business_tables_empty_after=True,public_revision_unchanged='0008',
            original_qa_rehearsal_connections=False,synthetic_schema_retained=True)
        (Path(__file__).parent/'evidence/beta-final-persistence.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2),flush=True)
        return int(code)
    finally:
        engine.dispose()
        event.remove(Engine,'before_cursor_execute',guard)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print('STOP: isolated test audit failed; category=' + type(error).__name__,flush=True)
        raise SystemExit(1) from None
