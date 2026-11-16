"""Opt-in persistence run in disposable schemas of the designated test database.

Run from backend: .venv/Scripts/python.exe persistence_schema_runner.py
The standard pytest fixtures continue to create their own disposable cluster.
"""
import importlib.util
from pathlib import Path
import re
import sys
from types import SimpleNamespace
from alembic import command
from alembic.config import Config
import psycopg
import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

spec = importlib.util.spec_from_file_location('isolated_session_fixtures', Path(__file__).parent / 'tests/session_integration/conftest.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)

if '--check-createdb' in sys.argv:
    source = fixtures.make_url(fixtures.Settings().database_url.get_secret_value())
    assert source.host in {'localhost', '127.0.0.1', '::1'} and (source.port or 5432) == 5432 and not source.query
    assert source.database == 'whatnot_app_dev'
    with psycopg.connect(host='127.0.0.1', port=5432, user=source.username, password=source.password,
            dbname=fixtures.TEST_DATABASE, connect_timeout=5,
            options='-c default_transaction_read_only=on -c statement_timeout=5000') as connection:
        assert fixtures.identity(connection) == (fixtures.TEST_DATABASE, fixtures.TEST_OID, True, '127.0.0.1', 5432)
        print('createdb:', connection.execute('SELECT rolcreatedb FROM pg_roles WHERE rolname=current_user').fetchone()[0])
    sys.exit(0)


def guard_schema(connection, cursor, statement, parameters, context, executemany):
    url = connection.engine.url
    assert url.database == fixtures.TEST_DATABASE
    match = re.search(r'(?:^| )-csearch_path=(whatnot_refresh_test_[a-f0-9]{32})(?: |$)', url.query.get('options', ''))
    assert match is not None, 'Every test engine must name its generated schema'
    schema = match.group(1)
    raw = connection.connection.driver_connection
    assert raw.info.dbname == fixtures.TEST_DATABASE
    if raw.info.transaction_status == psycopg.pq.TransactionStatus.INERROR:
        return
    with raw.cursor() as check:
        # Some legacy concurrency tests override connect_args.options. Restore
        # their URL's owned schema before their first SQL statement can execute.
        check.execute(psycopg.sql.SQL('SET search_path TO {}').format(psycopg.sql.Identifier(schema)))
        check.execute('SELECT current_database(),current_schema()')
        assert check.fetchone() == (fixtures.TEST_DATABASE, schema)


event.listen(Engine, 'before_cursor_execute', guard_schema)


@pytest.fixture(scope='session')
def persistence_migrated_schema_engine():
    owned = fixtures.session_engine.__wrapped__(SimpleNamespace(param='empty'))
    engine = next(owned)
    try:
        config = Config(str(Path(__file__).parent / 'alembic.ini'))
        config.attributes['database_url'] = engine.url
        command.upgrade(config, 'head')
        yield engine
    finally:
        owned.close()


@pytest.fixture
def persistence_fresh_schema_url():
    owned = fixtures.session_engine.__wrapped__(SimpleNamespace(param='empty'))
    engine = next(owned)
    try:
        yield engine.url
    finally:
        owned.close()


class SchemaSelection:
    def pytest_addoption(self, parser):
        parser.addoption('--persistence-isolated-schema', action='store_true')

try:
    sys.exit(pytest.main(['tests/persistence', '--persistence-isolated-schema', '-q', '--tb=short', *sys.argv[1:]], plugins=[sys.modules[__name__], SchemaSelection()]))
finally:
    event.remove(Engine, 'before_cursor_execute', guard_schema)
