"""Compile recovery DDL without connecting or applying a migration."""
from io import StringIO
from pathlib import Path
import runpy

from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_recovery_migration_emits_additive_postgresql_ddl():
    revision = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'alembic/versions/0011_password_recovery.py'))
    assert revision['revision'] == '0011'
    assert revision['down_revision'] == '0010'
    output = StringIO()
    context = MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': output})
    with Operations.context(context):
        revision['upgrade']()
    sql = output.getvalue()
    assert 'CREATE TABLE password_recoveries' in sql
    assert 'FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE' in sql
    assert 'UNIQUE (reset_digest)' in sql
    for column in ('user_id', 'email_digest', 'expires_at'):
        assert 'CREATE INDEX ix_password_recoveries_' + column in sql
    assert 'TIMESTAMP WITH TIME ZONE' in sql
    assert 'UPDATE ' not in sql and 'INSERT ' not in sql and 'DROP ' not in sql


def test_recovery_downgrade_refuses_history_without_deleting_it():
    revision = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'alembic/versions/0011_password_recovery.py'))
    output = StringIO()
    context = MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': output})
    with Operations.context(context):
        revision['downgrade']()
    sql = output.getvalue()
    # Prevent an issuer inserting history between the empty check and DROP.
    assert sql.index('LOCK TABLE password_recoveries IN ACCESS EXCLUSIVE MODE') < sql.index('IF EXISTS')
    assert sql.index('IF EXISTS (SELECT 1 FROM password_recoveries)') < sql.index('DROP TABLE password_recoveries')
    assert 'RAISE EXCEPTION' in sql
    assert 'DELETE ' not in sql and 'TRUNCATE ' not in sql


def test_revision_chain_has_one_head_and_no_missing_parents():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend = Path(__file__).resolve().parents[1]
    config = Config()
    config.set_main_option('script_location', str(backend / 'alembic'))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ['0011']
    revisions = list(scripts.walk_revisions())
    assert [revision.revision for revision in revisions] == [f'{value:04d}' for value in range(11, 0, -1)]
