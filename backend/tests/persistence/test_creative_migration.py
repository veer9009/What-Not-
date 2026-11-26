from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text
from conftest import migration_config

def test_domain_upgrade_preserves_legacy_and_downgrade_refuses_new_categories(fresh_database_url):
    config = migration_config(fresh_database_url)
    command.upgrade(config, '0013')
    engine = create_engine(fresh_database_url)
    try:
        with engine.begin() as connection:
            user = connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES('Provider','domain@creative.test','888002','test','SELLER') RETURNING id"))
            provider = connection.scalar(text("INSERT INTO creative_providers(user_id,display_name,bio) VALUES(:user,'Studio','Design') RETURNING id"), dict(user=user))
            listing = connection.scalar(text("INSERT INTO creative_listings(provider_id,title,description,category,pricing,currency,remote,portfolio,status) VALUES(:provider,'Legacy','Design','VFX','QUOTATION','INR',true,'[]','APPROVED') RETURNING id"), dict(provider=provider))
        command.upgrade(config, 'head')
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text("UPDATE creative_listings SET category='Website Development' WHERE id=:id"), dict(id=listing))
        with engine.begin() as connection:
            assert connection.scalar(text('SELECT domain FROM creative_listings WHERE id=:id'), dict(id=listing)) == 'CREATIVE'
            connection.execute(text("UPDATE creative_listings SET category='Website Development', domain='PROFESSIONAL' WHERE id=:id"), dict(id=listing))
        with pytest.raises(RuntimeError, match='Cannot downgrade'):
            command.downgrade(config, '0013')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT domain FROM creative_listings WHERE id=:id'), dict(id=listing)) == 'PROFESSIONAL'
        with engine.begin() as connection:
            connection.execute(text("UPDATE creative_listings SET domain='CREATIVE', category='VFX' WHERE id=:id"), dict(id=listing))
        command.downgrade(config, '0013')
        command.upgrade(config, 'head')
        with engine.connect() as connection:
            assert connection.execute(text('SELECT domain,category FROM creative_listings WHERE id=:id'), dict(id=listing)).one() == ('CREATIVE', 'VFX')
    finally:
        engine.dispose()


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
