import pytest
from alembic import command
from sqlalchemy import create_engine,event,text
from sqlalchemy.exc import OperationalError
from conftest import migration_config

def test_populated_wishlist_refuses_lossy_downgrade(fresh_database_url):
    config=migration_config(fresh_database_url);command.upgrade(config,'head')
    engine=create_engine(fresh_database_url)
    try:
        with engine.begin() as connection:
            buyer=connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES('Buyer','saved@test.example','saved','test','BUYER') RETURNING id"))
            connection.execute(text('INSERT INTO wishlist_items(buyer_id,product_id) VALUES(:buyer,99999)'),dict(buyer=buyer))
        with pytest.raises(RuntimeError,match='explicitly archived'):command.downgrade(config,'0014')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT count(*) FROM wishlist_items'))==1
            assert connection.scalar(text('SELECT version_num FROM alembic_version'))=='0015'
    finally:engine.dispose()

def test_shopping_downgrade_blocks_new_history_between_check_and_drop(fresh_database_url):
    config=migration_config(fresh_database_url);command.upgrade(config,'head')
    engine=create_engine(fresh_database_url)
    outcomes=[]
    try:
        with engine.begin() as connection:
            buyer=connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES('Buyer','race@test.example','race','test','BUYER') RETURNING id"))
        with engine.begin() as migration_connection:
            def attempt_history_write(connection,cursor,statement,parameters,context,executemany):
                if 'DROP COLUMN destination_revision' not in statement:return
                try:
                    with engine.begin() as contender:
                        contender.execute(text("SET LOCAL lock_timeout='200ms'"))
                        contender.execute(text('INSERT INTO wishlist_items(buyer_id,product_id) VALUES(:buyer,99999)'),dict(buyer=buyer))
                    outcomes.append('history inserted')
                except OperationalError as error:
                    assert error.orig.sqlstate=='55P03'
                    outcomes.append('history blocked')
            event.listen(migration_connection,'before_cursor_execute',attempt_history_write)
            config.attributes['connection']=migration_connection
            command.downgrade(config,'0014')
        assert outcomes==['history blocked'], 'Downgrade must never silently drop a concurrently saved product'
    finally:engine.dispose()
