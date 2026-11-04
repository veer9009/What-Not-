from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text
from conftest import migration_config


def test_empty_creative_downgrade_reupgrade_and_populated_refusal(fresh_database_url):
    config=migration_config(fresh_database_url)
    command.upgrade(config,'0007')
    engine=create_engine(fresh_database_url)
    try:
        assert 'creative_engagements' in inspect(engine).get_table_names()
        command.downgrade(config,'0006')
        assert 'creative_engagements' not in inspect(engine).get_table_names()
        command.upgrade(config,'0007')
        with engine.begin() as connection:
            user=connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES('Provider','migration@creative.test','888001','test','SELLER') RETURNING id"))
            connection.execute(text("INSERT INTO creative_providers(user_id,display_name,bio) VALUES(:user,'Studio','Design')"),dict(user=user))
        with pytest.raises(RuntimeError,match='preserve accepted terms'):
            command.downgrade(config,'0006')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT count(*) FROM creative_providers'))==1
    finally:
        engine.dispose()
