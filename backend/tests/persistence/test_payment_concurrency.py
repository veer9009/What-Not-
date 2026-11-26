from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models import User, SellerProfile, Address, Order
from app.models.payment import OrderPayment
from app.models.shopping import SellerPaymentSettings
from app.core.config import Settings
from app.models.events import AuditEvent
from app.schemas.payment import ConfirmationInput, ReportInput, MethodInput
from app.services.payments import PaymentService
from app.services.orders import OrderService
from app.services.errors import PersistenceConflict
from test_service_concurrency import concurrency_engine


def seed(engine,with_payment=True):
    with Session(engine,expire_on_commit=False) as session,session.begin():
        buyer=User(name='Buyer',email='race-buyer@example.test',phone='race-buyer',password_hash='test',role='BUYER')
        owner=User(name='Owner',email='race-owner@example.test',phone='race-owner',password_hash='test',role='SELLER')
        shop=SellerProfile(user=owner,shop_name='Race shop',phone='race-owner',latitude='19',longitude='72')
        address=Address(user=buyer,label='Home',address_line1='Test',city='Test',state='Test',pincode='400001',latitude='19',longitude='72')
        order=Order(buyer=buyer,seller=shop,address=address,status='ACCEPTED',subtotal=Decimal('0.30'),delivery_fee=Decimal('0.00'),total_amount=Decimal('0.30'))
        session.add(order);session.flush()
        if with_payment:session.add(OrderPayment(order_id=order.id,method='UPI',status='PENDING'))
        else:session.add(SellerPaymentSettings(seller_id=shop.id,upi_id='synthetic@example',account_holder_name='Synthetic seller',accept_cod=True,accept_upi=True,verification_status='APPROVED'))
        return buyer.id,owner.id,order.id


def test_concurrent_duplicate_confirmations_create_one_audit_event(concurrency_engine):
    buyer,owner,order=seed(concurrency_engine);barrier=Barrier(2)
    def confirm():
        with Session(concurrency_engine) as session,session.begin():
            barrier.wait(timeout=10)
            return PaymentService(session).confirm(owner,order,ConfirmationInput(expected_status='PENDING'))['status']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:confirm(),range(2)))
    assert results==['SELLER_CONFIRMED']*2
    with Session(concurrency_engine) as session:
        assert session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action=='PAYMENT_CONFIRMED'))==1


def test_buyer_report_racing_confirmation_cannot_overwrite_the_other_state(concurrency_engine):
    buyer,owner,order=seed(concurrency_engine);barrier=Barrier(2)
    def update(report):
        with Session(concurrency_engine) as session,session.begin():
            barrier.wait(timeout=10)
            try:
                service=PaymentService(session)
                return (service.report(buyer,order,ReportInput(reference='REF-123')) if report else service.confirm(owner,order,ConfirmationInput(expected_status='PENDING')))['status']
            except PersistenceConflict:return 'CONFLICT'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(update,[True,False]))
    assert results.count('CONFLICT')==1
    with Session(concurrency_engine) as session:
        row=session.get(OrderPayment,order)
        assert row.status in {'SELLER_CONFIRMED','BUYER_REPORTED'}
        assert (row.reference=='REF-123')==(row.status=='BUYER_REPORTED')
        assert session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.entity_type=='order_payment'))==1


def test_conflicting_first_methods_create_one_record_and_audit(concurrency_engine):
    buyer,owner,order=seed(concurrency_engine,with_payment=False);barrier=Barrier(2)
    def choose(method):
        with Session(concurrency_engine) as session,session.begin():
            barrier.wait(timeout=10)
            try:return PaymentService(session,Settings(_env_file=None,environment='test',prepaid_upi_enabled=True,approved_refund_policy_reference='SIMULATED-TEST-POLICY-ONLY')).record_method(buyer,order,MethodInput(method=method))['method']
            except PersistenceConflict:return 'CONFLICT'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(choose,['COD','UPI']))
    assert results.count('CONFLICT')==1
    with Session(concurrency_engine) as session:
        assert session.get(OrderPayment,order).method in {'COD','UPI'}
        assert session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.entity_type=='order_payment'))==1


def test_cancellation_racing_confirmation_preserves_only_a_prior_collection(concurrency_engine):
    buyer,owner,order=seed(concurrency_engine);barrier=Barrier(2)
    def update(cancel):
        with Session(concurrency_engine) as session,session.begin():
            barrier.wait(timeout=10)
            try:
                if cancel:
                    OrderService(session).transition(buyer,order,'CANCELLED')
                    return 'CANCELLED'
                return PaymentService(session).confirm(owner,order,ConfirmationInput(expected_status='PENDING'))['status']
            except PersistenceConflict:return 'CONFLICT'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(update,[True,False]))
    assert results[0]=='CANCELLED'
    assert results[1] in {'CONFLICT','SELLER_CONFIRMED'}
    with Session(concurrency_engine) as session:
        assert session.get(Order,order).status=='CANCELLED'
        payment=session.get(OrderPayment,order)
        assert payment.status==('SELLER_CONFIRMED' if results[1]=='SELLER_CONFIRMED' else 'PENDING')
        count=session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action=='PAYMENT_CONFIRMED'))
        assert count==(1 if payment.status=='SELLER_CONFIRMED' else 0)
