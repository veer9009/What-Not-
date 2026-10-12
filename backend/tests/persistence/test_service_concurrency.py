"""Real independent transactions in generated DBs inside the verified test cluster."""
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Barrier
import time

from alembic import command
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.models import Address, Order, Product, User
from conftest import migration_config
from test_services_marketplace import HASH, market


@pytest.fixture
def concurrency_engine(fresh_database_url):
    command.upgrade(migration_config(fresh_database_url), 'head')
    engine = create_engine(fresh_database_url, connect_args={
        'options': '-c lock_timeout=10000 -c statement_timeout=15000'})
    try:
        yield engine
    finally:
        engine.dispose()


def seed(engine):
    from app.services.inputs import UserCreate, AddressCreate
    with Session(engine, expire_on_commit=False) as session, session.begin():
        m = market.__wrapped__(session)
        m['moderation'].approve(m['admin'].id, m['product'].id)
        m['product'].stock_quantity = 1
        buyer2 = m['users'].create(UserCreate(name='Buyer 2', email='b2@example.com', phone='400', password_hash=HASH, role='BUYER'))
        address2 = m['addresses'].create(buyer2.id, AddressCreate(label='Home', address_line1='2 Lane', city='Mumbai', state='Maharashtra', pincode='400001', latitude=0, longitude=0))
        other = m['addresses'].create(m['buyer'].id, AddressCreate(label='Work', address_line1='3 Lane', city='Mumbai', state='Maharashtra', pincode='400001', latitude=0, longitude=0))
        return dict(buyer=m['buyer'].id, buyer2=buyer2.id, owner=m['owner'].id,
            seller=m['seller'].id, product=m['product'].id, address=m['address'].id,
            address2=address2.id, other_address=other.id)


def race_while_locked(engine, locked_query, operations, *, expected_query=None):
    """Prove both transactions contend before releasing the lock, without timing guesses."""
    barrier = Barrier(3)
    pids = Queue()

    def worker(operation):
        with Session(engine) as session, session.begin():
            pids.put(session.scalar(text('SELECT pg_backend_pid()')))
            barrier.wait(timeout=15)
            return operation(session)

    with ThreadPoolExecutor(max_workers=2) as pool:
        with engine.connect() as blocker, blocker.begin():
            blocker.execute(locked_query)
            futures = [pool.submit(worker, operation) for operation in operations]
            worker_ids = [pids.get(timeout=15), pids.get(timeout=15)]
            barrier.wait(timeout=15)
            deadline = time.monotonic() + 8
            with engine.connect() as observer:
                while time.monotonic() < deadline:
                    query = "SELECT count(*) FROM pg_stat_activity WHERE pid IN (:a,:b) AND wait_event_type='Lock'"
                    params = dict(a=worker_ids[0], b=worker_ids[1])
                    if expected_query:
                        query += ' AND query LIKE :fragment'
                        params['fragment'] = f'%{expected_query}%'
                    waiting = observer.scalar(text(query), params)
                    if waiting == 2:
                        break
                    observer.commit()  # refresh PostgreSQL's activity snapshot
                    time.sleep(0.02)
                else:
                    pytest.fail('Both transactions must demonstrably wait on database locks')
        return [future.result(timeout=20) for future in futures]


def test_concurrent_final_unit_cannot_be_sold_twice(concurrency_engine):
    from app.services.inputs import OrderPlacement
    from app.services.orders import OrderService
    from app.services.errors import ProductUnavailable, InsufficientStock
    engine = concurrency_engine
    r = seed(engine)

    def purchase(buyer, address):
        def operation(session):
            try:
                OrderService(session).create(OrderPlacement(buyer_id=buyer, seller_id=r['seller'], address_id=address, items=[dict(product_id=r['product'], quantity=1)]))
                return 'purchased'
            except (ProductUnavailable, InsufficientStock):
                return 'unavailable'
        return operation

    results = race_while_locked(engine, select(Product).where(Product.id == r['product']).with_for_update(),
        [purchase(r['buyer'], r['address']), purchase(r['buyer2'], r['address2'])], expected_query='FROM products')
    assert sorted(results) == ['purchased', 'unavailable']
    with Session(engine) as session:
        assert session.scalar(select(Product.stock_quantity).where(Product.id == r['product'])) == 0
        assert session.scalar(select(func.count()).select_from(Order)) == 1


def test_concurrent_terminal_transitions_restore_inventory_once(concurrency_engine):
    from app.services.inputs import OrderPlacement
    from app.services.orders import OrderService
    from app.services.errors import InvalidOrderTransition
    engine = concurrency_engine
    r = seed(engine)
    with Session(engine) as session, session.begin():
        order = OrderService(session).create(OrderPlacement(buyer_id=r['buyer'], seller_id=r['seller'], address_id=r['address'], items=[dict(product_id=r['product'], quantity=1)]))
        order_id = order.id

    def transition(actor, status):
        def operation(session):
            try:
                OrderService(session).transition(actor, order_id, status)
                return 'transitioned'
            except InvalidOrderTransition:
                return 'terminal'
        return operation

    results = race_while_locked(engine, select(Order).where(Order.id == order_id).with_for_update(),
        [transition(r['buyer'], 'CANCELLED'), transition(r['owner'], 'REJECTED')])
    assert sorted(results) == ['terminal', 'transitioned']
    with Session(engine) as session:
        assert session.scalar(select(Product.stock_quantity).where(Product.id == r['product'])) == 1
        assert session.scalar(select(Order.status).where(Order.id == order_id)) in {'CANCELLED', 'REJECTED'}


def test_concurrent_default_switches_leave_one_default(concurrency_engine):
    from app.services.addresses import AddressService
    engine = concurrency_engine
    r = seed(engine)

    def switch(address_id):
        def operation(session):
            AddressService(session).set_default(r['buyer'], address_id)
            return address_id
        return operation

    results = race_while_locked(engine, select(User).where(User.id == r['buyer']).with_for_update(),
        [switch(r['address']), switch(r['other_address'])])
    assert set(results) == {r['address'], r['other_address']}
    with Session(engine) as session:
        defaults = list(session.scalars(select(Address.id).where(Address.user_id == r['buyer'], Address.is_default.is_(True))))
        assert len(defaults) == 1 and defaults[0] in results
