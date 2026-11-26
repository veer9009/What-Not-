from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.models import Order, Product
from app.models.payment import OrderPayment
from app.models.shopping import CheckoutBatch
from app.services.checkout import CheckoutService
from test_service_concurrency import concurrency_engine,seed

def test_concurrent_identical_batches_return_one_order_and_payment(concurrency_engine):
    ids=seed(concurrency_engine);key=uuid4();barrier=Barrier(2)
    with Session(concurrency_engine) as session:
        price=str(session.get(Product,ids['product']).price)
    payload=dict(address_id=ids['address'],sellers=[dict(seller_id=ids['seller'],payment_method='COD',items=[dict(product_id=ids['product'],quantity=1,expected_unit_price=price)])])
    def place():
        with Session(concurrency_engine) as session,session.begin():
            barrier.wait(timeout=10)
            return CheckoutService(session).create(ids['buyer'],payload,key)['orders'][0].id
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:place(),range(2)))
    assert results[0]==results[1]
    with Session(concurrency_engine) as session:
        assert session.scalar(select(func.count()).select_from(CheckoutBatch))==1
        assert session.scalar(select(func.count()).select_from(OrderPayment))==1
        assert session.get(Product,ids['product']).stock_quantity==0
