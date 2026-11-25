import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from conftest import migration_config


def test_additive_payment_upgrade_preserves_orders_and_guards_populated_downgrade(fresh_database_url):
    config=migration_config(fresh_database_url)
    command.upgrade(config,'0012')
    engine=create_engine(fresh_database_url)
    try:
        with engine.begin() as connection:
            buyer=connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES('Buyer','paybuyer@test.example','paybuyer','test','BUYER') RETURNING id"))
            owner=connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES('Owner','payowner@test.example','payowner','test','SELLER') RETURNING id"))
            seller=connection.scalar(text("INSERT INTO seller_profiles(user_id,shop_name,phone,latitude,longitude) VALUES(:owner,'Shop','payowner',19,72) RETURNING id"),{'owner':owner})
            address=connection.scalar(text("INSERT INTO addresses(user_id,label,address_line1,city,state,pincode,latitude,longitude) VALUES(:buyer,'Home','Test','Test','Test','400001',19,72) RETURNING id"),{'buyer':buyer})
            order=connection.scalar(text("INSERT INTO orders(buyer_id,seller_id,address_id,status,subtotal,delivery_fee,total_amount) VALUES(:buyer,:seller,:address,'COMPLETED',250,0,250) RETURNING id"),dict(buyer=buyer,seller=seller,address=address))
        command.upgrade(config,'head')
        command.check(config)
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT count(*) FROM order_payments'))==0
            assert connection.execute(text('SELECT status,total_amount FROM orders WHERE id=:id'),{'id':order}).one()==('COMPLETED',250)
        command.downgrade(config,'0012')
        assert 'order_payments' not in inspect(engine).get_table_names()
        command.upgrade(config,'head')
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO order_payments(order_id,method,status) VALUES(:id,'COD','PENDING')"),{'id':order})
        with pytest.raises(Exception,match='payment history'):
            command.downgrade(config,'0012')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT count(*) FROM order_payments'))==1
            assert connection.scalar(text('SELECT count(*) FROM orders'))==1
    finally:engine.dispose()
