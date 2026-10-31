from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from conftest import migration_config


def test_delivery_migration_preserves_history_and_refuses_lossy_downgrade(fresh_database_url):
    config = migration_config(fresh_database_url)
    command.upgrade(config, '0003')
    engine = create_engine(fresh_database_url)
    try:
        with engine.begin() as connection:
            buyer = connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES ('Buyer','delivery-b@example.test','delivery-b','hash','BUYER') RETURNING id"))
            owner = connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES ('Seller','delivery-s@example.test','delivery-s','hash','SELLER') RETURNING id"))
            seller = connection.scalar(text("INSERT INTO seller_profiles(user_id,shop_name,phone,latitude,longitude) VALUES (:owner,'Maker','delivery-s',19,72) RETURNING id"), {'owner': owner})
            address = connection.scalar(text("INSERT INTO addresses(user_id,label,address_line1,city,state,pincode,latitude,longitude) VALUES (:buyer,'Home','Lane','Mumbai','Maharashtra','400001',19,72) RETURNING id"), {'buyer': buyer})
            values = dict(buyer=buyer, seller=seller, address=address)
            insert = text('INSERT INTO orders(buyer_id,seller_id,address_id,status,subtotal,delivery_fee,total_amount) VALUES (:buyer,:seller,:address,:status,250,0,250) RETURNING id')
            legacy = connection.scalar(insert, {**values, 'status': 'DELIVERED'})
            active = connection.scalar(insert, {**values, 'status': 'OUT_FOR_DELIVERY'})
        command.upgrade(config, 'head')
        command.check(config)
        with engine.begin() as connection:
            assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0004'
            assert connection.scalar(text('SELECT status FROM orders WHERE id=:id'), {'id': legacy}) == 'DELIVERED'
            connection.execute(text("UPDATE orders SET status='AWAITING_BUYER_CONFIRMATION' WHERE id=:id"), {'id': active})
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(text("UPDATE orders SET status='UNKNOWN' WHERE id=:id"), {'id': active})
        with pytest.raises(RuntimeError, match='awaiting buyer confirmation'):
            command.downgrade(config, '0003')
        with engine.begin() as connection:
            assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0004'
            assert connection.scalar(text('SELECT status FROM orders WHERE id=:id'), {'id': active}) == 'AWAITING_BUYER_CONFIRMATION'
            connection.execute(text("UPDATE orders SET status='DELIVERED' WHERE id=:id"), {'id': active})
        command.downgrade(config, '0003')
        assert next(c for c in inspect(engine).get_columns('orders') if c['name'] == 'status')['type'].length == 20
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM orders WHERE status='DELIVERED'")) == 2
        command.upgrade(config, 'head')
        command.check(config)
    finally:
        engine.dispose()
