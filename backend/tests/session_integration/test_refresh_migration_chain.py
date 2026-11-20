"""Alembic execution only in a newly generated, guarded disposable schema."""
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, text


@pytest.mark.parametrize('session_engine', ['empty'], indirect=True)
def test_current_head_upgrade_and_empty_downgrade(session_engine):
    backend = Path(__file__).resolve().parents[2]
    config = Config(str(backend / 'alembic.ini'))
    with session_engine.connect() as connection:
        config.attributes['connection'] = connection
        # An explicit verified connection prevents use of application settings.
        command.upgrade(config, '0009')
        before = set(inspect(connection).get_table_names())
        assert connection.scalar(text('SELECT count(*) FROM users')) == 0
        assert connection.scalar(text('SELECT count(*) FROM orders')) == 0
        connection.commit()
        command.upgrade(config, '0010')
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0010'
        assert set(inspect(connection).get_table_names()) - before == {'auth_sessions', 'auth_refresh_tokens'}
        connection.commit()
        command.downgrade(config, '0009')
        assert set(inspect(connection).get_table_names()) == before
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0009'
        assert connection.scalar(text('SELECT count(*) FROM users')) == 0
        assert connection.scalar(text('SELECT count(*) FROM orders')) == 0
        connection.commit()
        command.upgrade(config, 'head')
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0011'
        assert 'password_recoveries' in inspect(connection).get_table_names()
        connection.commit()
        command.downgrade(config, '0010')
        assert 'password_recoveries' not in inspect(connection).get_table_names()
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0010'
        connection.commit()
        command.upgrade(config, 'head')
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0011'
        connection.commit()
