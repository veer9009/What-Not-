from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import User, Order
from app.models.events import AuditEvent
from app.models.payment import OrderPayment
from app.services.payments import PaymentService
from app.schemas.payment import MethodInput, ReportInput, ConfirmationInput
from app.services.errors import OwnershipError, PersistenceConflict
from test_authentication import auth_client
from test_authorization import bearer

@pytest.fixture(autouse=True)
def simulated_upi_policy(monkeypatch,db,records,request):
    """Only isolated test records may exercise simulated prepaid UPI."""
    from app.core.config import Settings
    from app.models.shopping import SellerPaymentSettings
    settings=Settings(_env_file=None,environment='test',prepaid_upi_enabled=True,
        approved_refund_policy_reference='SIMULATED-TEST-POLICY-ONLY')
    monkeypatch.setattr('app.core.config.Settings',lambda **kwargs:settings)
    db.add(SellerPaymentSettings(seller_id=records['seller'].id,upi_id='synthetic@example',
        account_holder_name='Synthetic test seller',accept_cod=True,accept_upi=True,verification_status='APPROVED'))
    db.flush()
    if 'auth_client' in request.fixturenames:
        client=request.getfixturevalue('auth_client')
        client.app.state.settings.prepaid_upi_enabled=True
        client.app.state.settings.approved_refund_policy_reference='SIMULATED-TEST-POLICY-ONLY'


def method(service, records, value='UPI'):
    return service.record_method(records['buyer'].id, records['order'].id, MethodInput(method=value))


@pytest.mark.parametrize('reported', [False, True])
def test_confirmed_retries_require_the_same_reviewed_state(db, records, reported):
    service = PaymentService(db)
    method(service, records)
    records['order'].status = 'ACCEPTED'
    db.flush()
    buyer, seller, order = records['buyer'].id, records['seller_user'].id, records['order'].id
    expected = 'BUYER_REPORTED' if reported else 'PENDING'
    if reported:
        service.report(buyer, order, ReportInput(reference='RETRY-REFERENCE'))
    confirmed = service.confirm(seller, order, ConfirmationInput(expected_status=expected))
    conflicting = 'PENDING' if reported else 'BUYER_REPORTED'
    with pytest.raises(PersistenceConflict):
        service.confirm(seller, order, ConfirmationInput(expected_status=conflicting))
    retry = service.confirm(seller, order, ConfirmationInput(expected_status=expected))
    assert retry['confirmed_at'] == confirmed['confirmed_at']
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.entity_id == order, AuditEvent.action == 'PAYMENT_CONFIRMED')) == 1


def test_legacy_orders_are_unknown_and_never_inferred_from_delivery(db, records):
    records['order'].status = 'COMPLETED'
    db.flush()
    service = PaymentService(db)
    row = service.list(records['buyer'].id)['items'][0]
    assert row['method'] is None and row['status'] == 'NOT_RECORDED'
    assert row['confirmed_at'] is None and row['amount'] == '549.00'
    assert db.scalar(select(func.count()).select_from(OrderPayment)) == 0


def test_upi_reference_is_only_a_claim_and_confirmations_are_audited_once(db, records):
    service = PaymentService(db)
    method(service, records)
    records['order'].status = 'ACCEPTED'
    db.flush()
    buyer, seller, order = records['buyer'].id, records['seller_user'].id, records['order'].id
    row = service.report(buyer, order, ReportInput(reference='UTR-123456789012'))
    assert row['status'] == 'BUYER_REPORTED' and row['confirmed_at'] is None
    assert service.report(buyer, order, ReportInput(reference='UTR-123456789012'))['status'] == 'BUYER_REPORTED'
    with pytest.raises(PersistenceConflict):
        service.report(buyer, order, ReportInput(reference='DIFFERENT'))
    with pytest.raises(PersistenceConflict):
        service.confirm(seller, order, ConfirmationInput(expected_status='PENDING'))
    row = service.confirm(seller, order, ConfirmationInput(expected_status='BUYER_REPORTED'))
    assert row['status'] == 'SELLER_CONFIRMED' and row['confirmed_at'] is not None
    assert service.confirm(seller, order, ConfirmationInput(expected_status='BUYER_REPORTED'))['confirmed_at'] == row['confirmed_at']
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.entity_type == 'order_payment')))
    assert [e.action for e in events] == ['PAYMENT_METHOD_RECORDED', 'PAYMENT_REPORTED', 'PAYMENT_CONFIRMED']
    assert all('UTR-' not in (e.reason or '') for e in events)
    assert records['order'].status == 'ACCEPTED'


def test_cod_collection_is_separate_from_order_placement_and_delivery(db, records):
    service = PaymentService(db)
    method(service, records, 'COD')
    with pytest.raises(PersistenceConflict):
        service.confirm(records['seller_user'].id, records['order'].id, ConfirmationInput(expected_status='PENDING'))
    records['order'].status = 'DELIVERED'
    db.flush()
    assert service.list(records['seller_user'].id)['items'][0]['status'] == 'PENDING'
    with pytest.raises(PersistenceConflict):
        service.report(records['buyer'].id, records['order'].id, ReportInput())
    assert service.confirm(records['seller_user'].id, records['order'].id, ConfirmationInput(expected_status='PENDING'))['status'] == 'SELLER_CONFIRMED'


@pytest.mark.parametrize('role', ['BUYER', 'SELLER'])
def test_unrelated_accounts_cannot_read_or_mutate_other_payments(db, records, role):
    stranger=User(name='Other',email=f'other-{role}@example.test',phone=f'other-{role}',password_hash='test',role=role)
    db.add(stranger);db.flush()
    service=PaymentService(db)
    method(service, records)
    assert service.list(stranger.id)['items'] == []
    with pytest.raises(OwnershipError):
        service.get(stranger.id,records['order'].id)
    action=(lambda: service.record_method(stranger.id,records['order'].id,MethodInput(method='COD'))) if role=='BUYER' else (lambda:service.confirm(stranger.id,records['order'].id,ConfirmationInput(expected_status='PENDING')))
    with pytest.raises(OwnershipError):action()


def test_method_is_immutable_and_terminal_orders_do_not_accept_payment_changes(db, records):
    service=PaymentService(db);method(service, records)
    assert method(service, records)['method']=='UPI'
    with pytest.raises(PersistenceConflict):method(service, records, 'COD')
    records['order'].status='CANCELLED';db.flush()
    row=service.list(records['buyer'].id)['items'][0]
    assert not row['can_report'] and not row['can_select_method']
    with pytest.raises(PersistenceConflict):service.report(records['buyer'].id,records['order'].id,ReportInput())
    assert service.list(records['seller_user'].id)['items'][0]['can_confirm'] is False


def test_admin_aggregates_use_decimal_order_values_and_never_treat_collections_as_revenue(db, records):
    admin=User(name='Admin',email='payadmin@example.test',phone='payadmin',password_hash='test',role='ADMIN')
    db.add(admin);db.flush()
    service=PaymentService(db)
    initial=service.metrics(admin.id)
    assert initial['order_value']=='549.00' and initial['unrecorded_order_value']=='549.00'
    method(service, records,'COD');records['order'].status='DELIVERED';db.flush()
    assert service.metrics(admin.id)['pending_confirmation_count']==1
    service.confirm(records['seller_user'].id,records['order'].id,ConfirmationInput(expected_status='PENDING'))
    result=service.metrics(admin.id)
    assert result['cod_order_value']=='549.00' and result['seller_confirmed_value']=='549.00'
    assert result['platform_revenue']=='0.00' and result['pending_confirmation_count']==0
    records['order'].status='CANCELLED';db.flush()
    assert service.metrics(admin.id)['cancelled_confirmed_value']=='549.00'
    assert service.get(admin.id,records['order'].id)['status']=='SELLER_CONFIRMED'


def test_real_api_role_checks_field_validation_and_private_order_scope(auth_client, db, records):
    order=records['order'].id
    buyer=bearer(records['buyer'].id);seller=bearer(records['seller_user'].id)
    assert auth_client.get('/api/v1/payments').status_code==401
    assert auth_client.get('/api/v1/payments/metrics',headers=buyer).status_code==403
    assert auth_client.post(f'/api/v1/payments/orders/{order}/method',headers=seller,json={'method':'UPI'}).status_code==403
    for body in [{'method':'CARD'},{'method':'UPI','buyer_id':9},{'method':'UPI','amount':'0.01'}]:
        assert auth_client.post(f'/api/v1/payments/orders/{order}/method',headers=buyer,json=body).status_code==422
    assert auth_client.post(f'/api/v1/payments/orders/{order}/method',headers=buyer,json={'method':'UPI'}).status_code==200
    records['order'].status='ACCEPTED';db.flush()
    assert auth_client.post(f'/api/v1/payments/orders/{order}/report',headers=buyer,json={'reference':'<script>alert(1)</script>'}).status_code==422
    assert auth_client.post(f'/api/v1/payments/orders/{order}/report',headers=buyer,json={'reference':'REF-123456789'}).json()['status']=='BUYER_REPORTED'
    assert auth_client.post(f'/api/v1/payments/orders/{order}/confirm',headers=buyer,json={'expected_status':'BUYER_REPORTED'}).status_code==403
    assert auth_client.post(f'/api/v1/payments/orders/{order}/confirm',headers=seller,json={'expected_status':'BUYER_REPORTED'}).json()['status']=='SELLER_CONFIRMED'
    assert auth_client.get('/api/v1/payments',headers=buyer).json()['items'][0]['amount']=='549.00'


@pytest.mark.parametrize('role',['BUYER','SELLER'])
def test_real_api_rejects_cross_account_access_and_forged_admin_role(auth_client,db,records,role):
    stranger=User(name='Stranger',email=f'api-{role}@example.test',phone=f'api-{role}',password_hash='test',role=role)
    db.add(stranger);db.flush()
    headers=bearer(stranger.id,role='ADMIN');order=records['order'].id
    assert auth_client.get('/api/v1/payments',headers=headers).json()['items']==[]
    assert auth_client.get(f'/api/v1/payments/orders/{order}',headers=headers).status_code==403
    assert auth_client.get('/api/v1/payments/metrics',headers=headers).status_code==403
    path='report' if role=='BUYER' else 'confirm'
    payload={} if role=='BUYER' else {'expected_status':'PENDING'}
    assert auth_client.post(f'/api/v1/payments/orders/{order}/{path}',headers=headers,json=payload).status_code==403


def test_metrics_are_exact_across_pages_and_include_unknown_method_values(db,records):
    admin=User(name='Admin',email='decimal-admin@example.test',phone='decimal-admin',password_hash='test',role='ADMIN')
    db.add(admin)
    for amount in ['0.10','0.20']:
        db.add(Order(buyer_id=records['buyer'].id,seller_id=records['seller'].id,address_id=records['address'].id,
            status='PLACED',subtotal=Decimal(amount),delivery_fee=Decimal('0.00'),total_amount=Decimal(amount)))
    db.flush();service=PaymentService(db)
    page=service.list(admin.id,limit=1)
    assert len(page['items'])==1 and page['has_more'] is True
    metrics=service.metrics(admin.id)
    assert metrics['order_count']==3
    assert metrics['order_value']=='549.30' and metrics['unrecorded_order_value']=='549.30'
    assert metrics['seller_confirmed_value']=='0.00' and metrics['pending_confirmation_count']==0
