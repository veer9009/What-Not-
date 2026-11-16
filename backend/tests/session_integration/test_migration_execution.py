"""Exercise only synthetic test tables, rolling all DDL back afterward."""
from pathlib import Path
import runpy

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text, inspect
from sqlalchemy.exc import DBAPIError


def test_upgrade_empty_downgrade_and_history_guard(session_engine):
    revision = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'alembic/versions/0010_auth_sessions.py'))
    with session_engine.connect() as connection:
        transaction = connection.begin()
        try:
            before = {name: connection.scalar(text(f'SELECT count(*) FROM {name}'))
                      for name in ('users', 'orders')}
            connection.execute(text('DROP TABLE auth_refresh_tokens'))
            connection.execute(text('DROP TABLE auth_sessions'))
            with Operations.context(MigrationContext.configure(connection)):
                revision['upgrade']()
                assert {'auth_sessions', 'auth_refresh_tokens'} <= set(inspect(connection).get_table_names())
                assert {column['name'] for column in inspect(connection).get_columns('auth_sessions')
                        if getattr(column['type'], 'timezone', False)} == {'created_at', 'expires_at', 'revoked_at'}
                revision['downgrade']()
                assert 'auth_sessions' not in inspect(connection).get_table_names()
                revision['upgrade']()
                # Synthetic identity only; no application or public-schema records.
                user_id = connection.scalar(text("INSERT INTO users (name,email,phone,password_hash,role,is_active,created_at,updated_at) VALUES ('Migration Test','migration-isolated@example.com','migration-only','unusable','BUYER',true,now(),now()) RETURNING id"))
                connection.execute(text("INSERT INTO auth_sessions (id,user_id,role,created_at,expires_at) VALUES (:id,:user,'BUYER',now(),now()+interval '8 hours')"), {'id':'f'*32,'user':user_id})
                savepoint = connection.begin_nested()
                with pytest.raises(DBAPIError, match='Refusing downgrade'):
                    revision['downgrade']()
                savepoint.rollback()
                assert connection.scalar(text('SELECT count(*) FROM auth_sessions')) == 1
            assert connection.scalar(text('SELECT count(*) FROM orders')) == before['orders']
            assert connection.scalar(text('SELECT count(*) FROM users')) == before['users'] + 1
        finally:
            transaction.rollback()
