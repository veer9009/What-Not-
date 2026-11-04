from uuid import uuid4

from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from conftest import migration_config


def test_idempotency_migration_preserves_legacy_orders_and_enforces_uniqueness(fresh_database_url):
    config = migration_config(fresh_database_url)
    command.upgrade(config, '0002')
    engine = create_engine(fresh_database_url)
    try:
        with engine.begin() as connection:
            buyer = connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES ('Buyer','legacy-idem-b@example.test','idem-b','hash','BUYER') RETURNING id"))
            owner = connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES ('Seller','legacy-idem-s@example.test','idem-s','hash','SELLER') RETURNING id"))
            seller = connection.scalar(text("INSERT INTO seller_profiles(user_id,shop_name,phone,latitude,longitude) VALUES (:owner,'Maker','idem-s',19,72) RETURNING id"), {'owner': owner})
            address = connection.scalar(text("INSERT INTO addresses(user_id,label,address_line1,city,state,pincode,latitude,longitude) VALUES (:buyer,'Home','Lane','Mumbai','Maharashtra','400001',19,72) RETURNING id"), {'buyer': buyer})
            legacy = connection.scalar(text("INSERT INTO orders(buyer_id,seller_id,address_id,subtotal,delivery_fee,total_amount) VALUES (:buyer,:seller,:address,250,0,250) RETURNING id"), dict(buyer=buyer, seller=seller, address=address))
        command.upgrade(config, '0003')
        constraints = {item['name'] for item in inspect(engine).get_unique_constraints('orders')}
        assert 'uq_orders_buyer_id_idempotency_key' in constraints
        with engine.begin() as connection:
            old = connection.execute(text('SELECT idempotency_key,request_fingerprint,total_amount FROM orders WHERE id=:id'), {'id': legacy}).one()
            assert old[0] is None and old[1] is None and old[2] == 250
            values = dict(buyer=buyer, seller=seller, address=address, key=uuid4(), fingerprint='a' * 64)
            sql = text('INSERT INTO orders(buyer_id,seller_id,address_id,subtotal,delivery_fee,total_amount,idempotency_key,request_fingerprint) VALUES (:buyer,:seller,:address,250,0,250,:key,:fingerprint)')
            connection.execute(sql, values)
            with pytest.raises(IntegrityError) as caught, connection.begin_nested():
                connection.execute(sql, values)
            assert caught.value.orig.diag.constraint_name == 'uq_orders_buyer_id_idempotency_key'
        command.downgrade(config, '0002')
        assert 'idempotency_key' not in {column['name'] for column in inspect(engine).get_columns('orders')}
        command.upgrade(config, '0003')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT count(*) FROM orders')) == 2
    finally:
        engine.dispose()
