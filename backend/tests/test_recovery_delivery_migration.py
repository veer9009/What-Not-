"""Compile 0012 offline. Never connect or execute database migrations."""
from io import StringIO
from pathlib import Path
import runpy
from alembic.migration import MigrationContext
from alembic.operations import Operations


def compile_revision(operation):
    revision = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'alembic/versions/0012_recovery_deliveries.py'))
    assert revision['revision'] == '0012' and revision['down_revision'] == '0011'
    output = StringIO()
    context = MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': output})
    with Operations.context(context):
        revision[operation]()
    return output.getvalue()


def test_encrypted_outbox_upgrade_is_additive_postgresql_ddl():
    sql = compile_revision('upgrade')
    assert 'CREATE TABLE recovery_deliveries' in sql and 'BYTEA' in sql
    assert 'TIMESTAMP WITH TIME ZONE' in sql
    assert 'REFERENCES password_recoveries (challenge) ON DELETE RESTRICT' in sql
    assert 'REFERENCES users (id) ON DELETE RESTRICT' in sql
    assert 'ck_recovery_deliveries_payload' in sql
    assert 'ck_recovery_deliveries_lease' in sql
    for column in ('user_id', 'expires_at', 'next_attempt_at', 'lease_until'):
        assert 'CREATE INDEX ix_recovery_deliveries_' + column in sql
    assert not any(statement.strip().startswith(('UPDATE ', 'INSERT ', 'DROP ', 'DELETE ')) for statement in sql.split(';'))


def test_delivery_downgrade_locks_and_refuses_history():
    sql = compile_revision('downgrade')
    assert sql.index('LOCK TABLE') < sql.index('IF EXISTS') < sql.index('DROP TABLE')
    assert 'RAISE EXCEPTION' in sql and 'DELETE ' not in sql
