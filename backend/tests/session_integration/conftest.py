"""Synthetic PostgreSQL schema only. Never run Alembic or touch application records."""
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.db.base import Base
import app.models

TEST_DATABASE = 'whatnot_tests_20261115_a7e394c2'
TEST_OID = 49265


def identity(connection):
    return connection.execute("""SELECT current_database(),oid::bigint,
        datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user),
        host(inet_server_addr()),inet_server_port() FROM pg_database
        WHERE datname=current_database()""").fetchone()


def public_snapshot(connection):
    tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
    counts = {}
    for (table,) in tables:
        counts[table] = connection.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(table))).fetchone()[0]
    revision = connection.execute('SELECT version_num FROM public.alembic_version').fetchall()
    return tables, counts, revision


@pytest.fixture(scope='session')
def session_engine(request):
    source = make_url(Settings().database_url.get_secret_value())
    assert source.host in {'localhost','127.0.0.1','::1'} and (source.port or 5432)==5432 and not source.query
    assert source.database == 'whatnot_app_dev'
    args = dict(host='127.0.0.1',port=5432,user=source.username,password=source.password,
                dbname=TEST_DATABASE,connect_timeout=5)
    # Verify a previously designated test database, never fall back to application/QA.
    with psycopg.connect(**args,options='-c default_transaction_read_only=on -c statement_timeout=5000') as connection:
        assert identity(connection)==(TEST_DATABASE,TEST_OID,True,'127.0.0.1',5432)
        before = public_snapshot(connection)
        assert all(before[1].get(table)==0 for table in ('users','seller_profiles','products','addresses','orders'))
    schema = 'whatnot_refresh_test_' + uuid4().hex
    assert len(schema)<63 and schema.startswith('whatnot_refresh_test_')
    with psycopg.connect(**args) as connection:
        assert identity(connection)==(TEST_DATABASE,TEST_OID,True,'127.0.0.1',5432)
        assert not connection.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(schema,)).fetchone()
        connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    url=source.set(host='127.0.0.1',database=TEST_DATABASE,
                   query={'options':f'-csearch_path={schema} -clock_timeout=5000 -cstatement_timeout=15000 -cTimeZone=Asia/Kolkata'})
    engine=create_engine(url,hide_parameters=True,pool_size=6,max_overflow=2)
    def guard(connection,cursor,statement,parameters,context,executemany):
        raw=connection.connection.driver_connection
        assert raw.info.dbname==TEST_DATABASE
        if raw.info.transaction_status==psycopg.pq.TransactionStatus.INERROR:
            return  # Only SQLAlchemy transaction recovery can succeed in this state.
        with raw.cursor() as check:
            check.execute('SELECT current_database(),current_schema()')
            assert check.fetchone()==(TEST_DATABASE,schema)
    event.listen(engine,'before_cursor_execute',guard)
    try:
        # ORM DDL in a newly generated test-only schema, NOT an Alembic migration.
        if getattr(request, 'param', 'orm') != 'empty':
            Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with psycopg.connect(**args) as connection:
            assert identity(connection)==(TEST_DATABASE,TEST_OID,True,'127.0.0.1',5432)
            assert public_snapshot(connection)==before
            assert schema.startswith('whatnot_refresh_test_') and len(schema)==53
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
            assert public_snapshot(connection)==before
