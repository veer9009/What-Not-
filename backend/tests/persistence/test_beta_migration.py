from alembic import command
import pytest
from sqlalchemy import create_engine, text
from conftest import migration_config


def test_beta_populated_migration_keeps_legacy_consent_unknown(fresh_database_url):
    config = migration_config(fresh_database_url)
    command.upgrade(config, '0004')
    engine = create_engine(fresh_database_url)
    try:
        with engine.begin() as connection:
            buyer = connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES ('Buyer','beta-b@example.test','beta-b','hash','BUYER') RETURNING id"))
            owner = connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES ('Owner','beta-s@example.test','beta-s','hash','SELLER') RETURNING id"))
            seller = connection.scalar(text("INSERT INTO seller_profiles(user_id,shop_name,phone,latitude,longitude) VALUES (:id,'Maker','beta-s',19,72) RETURNING id"), {'id': owner})
            address = connection.scalar(text("INSERT INTO addresses(user_id,label,address_line1,city,state,pincode,latitude,longitude) VALUES (:id,'Home','Lane','Mumbai','MH','400001',19,72) RETURNING id"), {'id': buyer})
            for status in ('DELIVERED', 'AWAITING_BUYER_CONFIRMATION'):
                connection.execute(text('INSERT INTO orders(buyer_id,seller_id,address_id,status,subtotal,delivery_fee,total_amount) VALUES (:buyer,:seller,:address,:status,10,0,10)'), dict(buyer=buyer, seller=seller, address=address, status=status))
        command.upgrade(config, '0005')
        with engine.connect() as connection:
            rows = connection.execute(text('SELECT status,completion_source,delivered_at,completed_at,confirmation_deadline FROM orders ORDER BY id')).all()
            assert rows[0] == ('COMPLETED', 'LEGACY', None, None, None)
            assert rows[1][:4] == ('DELIVERED', 'MIGRATION', None, None)
            assert rows[1][4] is not None
            assert connection.scalar(text('SELECT count(*) FROM audit_events')) == 2
        with pytest.raises(RuntimeError, match='data loss'):
            command.downgrade(config, '0004')
    finally:
        engine.dispose()
