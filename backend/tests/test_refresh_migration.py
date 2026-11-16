"""Compile/review migration SQL only. No engine, connection or migration execution."""
from io import StringIO
from pathlib import Path
import runpy

from alembic.migration import MigrationContext
from alembic.operations import Operations


def emitted(direction):
    revision=runpy.run_path(str(Path(__file__).resolve().parents[1]/'alembic/versions/0010_auth_sessions.py'))
    assert revision['revision']=='0010' and revision['down_revision']=='0009'
    output=StringIO()
    context=MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':output})
    with Operations.context(context):
        revision[direction]()
    return output.getvalue()


def test_upgrade_sql_adds_only_session_tables_indexes_and_foreign_keys():
    sql=emitted('upgrade')
    assert 'CREATE TABLE auth_sessions' in sql
    assert 'CREATE TABLE auth_refresh_tokens' in sql
    assert 'REFERENCES users (id) ON DELETE CASCADE' in sql
    assert 'REFERENCES auth_sessions (id) ON DELETE CASCADE' in sql
    assert 'CREATE INDEX ix_auth_sessions_user_id' in sql
    assert 'CREATE INDEX ix_auth_sessions_expires_at' in sql
    assert 'CREATE INDEX ix_auth_refresh_tokens_session_id' in sql
    assert 'UPDATE ' not in sql and 'INSERT ' not in sql and 'ALTER TABLE products' not in sql


def test_downgrade_sql_refuses_history_loss_before_drop_and_obeys_fk_order():
    sql=emitted('downgrade')
    assert 'IF EXISTS (SELECT 1 FROM auth_sessions)' in sql
    assert sql.index('RAISE EXCEPTION')<sql.index('DROP TABLE auth_refresh_tokens')
    assert sql.index('DROP TABLE auth_refresh_tokens')<sql.index('DROP TABLE auth_sessions')
