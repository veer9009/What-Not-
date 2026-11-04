from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import Order
from app.models.events import AuditEvent
from app.services.orders import OrderService
from app.services.inputs import OrderPlacement
from app.services.errors import InvalidOrderTransition
from test_service_concurrency import concurrency_engine, seed


def test_dispute_and_timeout_independent_transactions_have_one_winner(concurrency_engine):
    engine = concurrency_engine
    identities = seed(engine)
    with Session(engine) as session, session.begin():
        order = OrderService(session).create(OrderPlacement(buyer_id=identities['buyer'], seller_id=identities['seller'],
            address_id=identities['address'], items=[dict(product_id=identities['product'], quantity=1)]))
        order.status = 'DELIVERED'
        order.confirmation_deadline = datetime.now(timezone.utc) - timedelta(seconds=1)
        order_id = order.id
    barrier = Barrier(2)

    def dispute():
        with Session(engine) as session, session.begin():
            barrier.wait(timeout=10)
            try:
                OrderService(session).transition(identities['buyer'], order_id, 'DELIVERY_DISPUTED')
                return 1
            except InvalidOrderTransition:
                return 0

    def complete():
        with Session(engine) as session, session.begin():
            barrier.wait(timeout=10)
            return OrderService(session).auto_complete_due()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(dispute)
        second = pool.submit(complete)
        assert first.result(timeout=20) + second.result(timeout=20) == 1
    with Session(engine) as session:
        status = session.get(Order, order_id).status
        assert status in {'DELIVERY_DISPUTED', 'COMPLETED'}
        assert session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.entity_id == order_id,
            AuditEvent.next_status.in_(['DELIVERY_DISPUTED', 'COMPLETED']))) == 1


def test_outbox_claim_skips_an_independent_transaction_lease_lock(concurrency_engine):
    from types import SimpleNamespace
    from app.services.workers import claim_email_batch
    from app.services.notifications import publish_event
    engine = concurrency_engine
    identities = seed(engine)
    with Session(engine) as session, session.begin():
        publish_event(session, identities['buyer'], 'claim-race:1', 'TEST', 'order', 1, 'Update', 'Body')
    config = SimpleNamespace(outbox_batch_size=1, outbox_max_attempts=2, outbox_lease_seconds=120)
    with Session(engine) as first, first.begin():
        claim = claim_email_batch(first, config)
        assert len(claim) == 1
        first.flush()
        with Session(engine) as second, second.begin():
            assert claim_email_batch(second, config) == []


def test_slow_email_runner_cannot_overlap_or_prelease_later_messages(concurrency_engine, monkeypatch):
    from types import SimpleNamespace
    import app.services.workers as workers
    from app.models.events import EmailOutbox
    from app.services.notifications import publish_event
    engine = concurrency_engine
    identities = seed(engine)
    with Session(engine) as session, session.begin():
        for number in range(2):
            publish_event(session, identities['buyer'], f'slow:{number}', 'TEST', 'order', 1, 'Update', 'Body')
    moment = [datetime.now(timezone.utc) + timedelta(seconds=1)]

    class Clock:
        @staticmethod
        def now(tz=None):
            return moment[0]

    monkeypatch.setattr(workers, 'datetime', Clock)
    config = SimpleNamespace(email_provider='disabled', outbox_batch_size=2, outbox_max_attempts=5,
        outbox_lease_seconds=120, outbox_backoff_seconds=60)

    class SlowProvider:
        def __init__(self):
            self.sent = []
            self.overlapped = False

        def send(self, recipient, title, body, key):
            self.sent.append(key)
            if not self.overlapped:
                self.overlapped = True
                with Session(engine) as observer:
                    states = list(observer.scalars(select(EmailOutbox.state).order_by(EmailOutbox.id)))
                    assert states == ['LEASED', 'PENDING']
                moment[0] += timedelta(seconds=121)
                workers.process_email(engine, config, self)
            return key

    provider = SlowProvider()
    workers.process_email(engine, config, provider)
    assert len(provider.sent) == len(set(provider.sent)) == 2
    with Session(engine) as session:
        assert list(session.scalars(select(EmailOutbox.state))) == ['SENT', 'SENT']
        assert list(session.scalars(select(EmailOutbox.attempts))) == [1, 1]
