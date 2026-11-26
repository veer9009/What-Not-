"""Owned direct-payment records, serialized on the existing order lock.

Payment confirmation is a seller attestation, never bank/gateway verification.
"""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import case, func, select
from app.models import Order, SellerProfile
from app.models.payment import OrderPayment
from app.models.events import AuditEvent
from app.schemas.payment import MethodInput, ReportInput, ConfirmationInput
from app.services.errors import InvalidRole, OrderNotFound, OwnershipError, PersistenceConflict
from app.services.operations import write_operation
from app.services.users import pagination, require_user

ACTIVE={'ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','COMPLETED','DELIVERY_DISPUTED'}
TERMINAL={'CANCELLED','REJECTED'}


class PaymentService:
    def __init__(self,session,settings=None):
        from app.core.config import Settings
        self.session=session;self.settings=settings or Settings(_env_file=None)

    def _scope(self,actor):
        if actor.role=='BUYER':return Order.buyer_id==actor.id
        if actor.role=='SELLER':return SellerProfile.user_id==actor.id
        if actor.role=='ADMIN':return True
        raise InvalidRole('Payment records are unavailable for this role')

    def _owned(self,actor,order_id,lock=False):
        query=select(Order).where(Order.id==order_id)
        if lock:query=query.with_for_update().execution_options(populate_existing=True)
        order=self.session.scalar(query)
        if order is None:raise OrderNotFound('Order does not exist')
        seller=self.session.get(SellerProfile,order.seller_id)
        if actor.role!='ADMIN' and not (actor.role=='BUYER' and order.buyer_id==actor.id or actor.role=='SELLER' and seller.user_id==actor.id):
            raise OwnershipError('Payment belongs to another buyer or seller')
        return order,seller

    def _view(self,actor,order,seller,payment):
        active=order.status in ACTIVE
        status=payment.status if payment else 'NOT_RECORDED'
        return dict(order_id=order.id,seller_id=seller.id,seller_name=seller.shop_name,
            amount=format(Decimal(order.total_amount),'.2f'),currency='INR',order_status=order.status,order_date=order.created_at,
            method=payment.method if payment else None,status=status,reference=payment.reference if payment else None,
            reported_at=payment.reported_at if payment else None,confirmed_at=payment.confirmed_at if payment else None,
            can_select_method=actor.role=='BUYER' and payment is None and order.status not in TERMINAL,
            can_report=actor.role=='BUYER' and order.status in ACTIVE|{'PLACED'} and payment is not None and payment.method=='UPI' and status=='PENDING',
            can_confirm=actor.role=='SELLER' and payment is not None and status!='SELLER_CONFIRMED' and active
                and (payment.method=='UPI' or order.status in {'DELIVERED','COMPLETED'}))

    def get(self,actor_id,order_id):
        actor=require_user(self.session,actor_id)
        order,seller=self._owned(actor,order_id)
        return self._view(actor,order,seller,self.session.get(OrderPayment,order_id))

    def list(self,actor_id,*,offset=0,limit=50):
        actor=require_user(self.session,actor_id)
        pagination(offset,limit)
        rows=self.session.execute(select(Order,SellerProfile,OrderPayment).join(SellerProfile,Order.seller_id==SellerProfile.id)
            .outerjoin(OrderPayment,OrderPayment.order_id==Order.id).where(self._scope(actor))
            .order_by(Order.id.desc()).offset(offset).limit(limit+1)).all()
        return dict(items=[self._view(actor,*row) for row in rows[:limit]],has_more=len(rows)>limit)

    def _payment(self,order_id):
        return self.session.scalar(select(OrderPayment).where(OrderPayment.order_id==order_id)
            .execution_options(populate_existing=True))

    def _audit(self,actor,order_id,action,previous,status):
        self.session.add(AuditEvent(actor_id=actor.id,actor_type='USER',entity_type='order_payment',entity_id=order_id,
            action=action,previous_status=previous,next_status=status,reason='Direct payment record; not bank verified'))

    @write_operation
    def record_method(self,actor_id,order_id,data):
        data=MethodInput.model_validate(data)
        actor=require_user(self.session,actor_id,role='BUYER',lock=True)
        order,seller=self._owned(actor,order_id,True)
        payment=self._payment(order_id)
        if payment:
            if payment.method!=data.method:raise PersistenceConflict('The recorded payment method cannot be changed')
            return self._view(actor,order,seller,payment)
        if order.status in TERMINAL:raise PersistenceConflict('Cancelled or rejected orders cannot record a new payment method')
        from app.services.payment_settings import PaymentSettingsService
        service=PaymentSettingsService(self.session,self.settings)
        destination=service.row(seller.id,True)
        if data.method=='UPI' and service.reason(destination):raise PersistenceConflict(service.reason(destination))
        if data.method=='COD' and destination and not destination.accept_cod:raise PersistenceConflict('Seller does not accept cash on delivery')
        payment=OrderPayment(order_id=order_id,method=data.method,status='PENDING',
            destination_upi_id=destination.upi_id if data.method=='UPI' else None,
            destination_name=destination.account_holder_name if data.method=='UPI' else None,
            destination_revision=destination.revision if data.method=='UPI' else None)
        self.session.add(payment);self.session.flush()
        self._audit(actor,order_id,'PAYMENT_METHOD_RECORDED',None,'PENDING')
        self._notify(order,seller,'METHOD','Payment method recorded',f'{data.method} order: INR {order.total_amount}. Awaiting collection.')
        return self._view(actor,order,seller,payment)

    @write_operation
    def report(self,actor_id,order_id,data):
        data=ReportInput.model_validate(data)
        actor=require_user(self.session,actor_id,role='BUYER',lock=True)
        order,seller=self._owned(actor,order_id,True);payment=self._payment(order_id)
        if not payment or payment.method!='UPI':raise PersistenceConflict('Select direct UPI before reporting payment')
        if payment.reported_at is not None:
            if payment.reference!=data.reference:raise PersistenceConflict('A different payment reference is already recorded')
            return self._view(actor,order,seller,payment)
        if order.status not in ACTIVE|{'PLACED'} or payment.status!='PENDING':raise PersistenceConflict('This order cannot accept a payment report')
        payment.reference=data.reference;payment.reported_at=datetime.now(timezone.utc);payment.status='BUYER_REPORTED'
        self._audit(actor,order_id,'PAYMENT_REPORTED','PENDING',payment.status)
        self._notify(order,seller,'REPORTED','Payment awaiting verification','Buyer reported UPI payment. Seller must independently confirm receipt.')
        return self._view(actor,order,seller,payment)

    @write_operation
    def confirm(self,actor_id,order_id,data):
        data=ConfirmationInput.model_validate(data)
        actor=require_user(self.session,actor_id,role='SELLER',lock=True)
        order,seller=self._owned(actor,order_id,True);payment=self._payment(order_id)
        if not payment:raise PersistenceConflict('No payment method has been recorded')
        if payment.status=='SELLER_CONFIRMED':
            reviewed_status='BUYER_REPORTED' if payment.reported_at is not None else 'PENDING'
            if data.expected_status!=reviewed_status:raise PersistenceConflict('The payment record changed; refresh before confirming')
            return self._view(actor,order,seller,payment)
        if payment.status!=data.expected_status:raise PersistenceConflict('The payment record changed; refresh before confirming')
        if not self._view(actor,order,seller,payment)['can_confirm']:raise PersistenceConflict('Collection cannot be confirmed in this order state')
        previous=payment.status;payment.status='SELLER_CONFIRMED';payment.confirmed_at=datetime.now(timezone.utc)
        self._audit(actor,order_id,'PAYMENT_CONFIRMED',previous,payment.status)
        self._notify(order,seller,'CONFIRMED','Payment receipt confirmed','Seller confirmed receipt. This is a seller attestation, not bank verification.')
        return self._view(actor,order,seller,payment)

    def metrics(self,actor_id):
        require_user(self.session,actor_id,role='ADMIN')
        zero=Decimal('0.00')
        def value(condition=True):return func.coalesce(func.sum(case((condition,Order.total_amount),else_=zero)),zero)
        def count(condition):return func.count(case((condition,Order.id)))
        confirmed=OrderPayment.status=='SELLER_CONFIRMED'
        cancelled=Order.status.in_(TERMINAL)
        fields=dict(order_count=func.count(Order.id),order_value=value(),cod_order_value=value(OrderPayment.method=='COD'),
            upi_order_value=value(OrderPayment.method=='UPI'),unrecorded_order_value=value(OrderPayment.order_id.is_(None)),
            buyer_reported_count=count(OrderPayment.reported_at.is_not(None)),buyer_reported_value=value(OrderPayment.reported_at.is_not(None)),
            seller_confirmed_count=count(confirmed),seller_confirmed_value=value(confirmed),
            pending_confirmation_count=count(OrderPayment.order_id.is_not(None)&~confirmed&~cancelled),
            cancelled_order_value=value(cancelled),cancelled_confirmed_value=value(cancelled&confirmed))
        row=self.session.execute(select(*(expr.label(key) for key,expr in fields.items())).select_from(Order)
            .outerjoin(OrderPayment,OrderPayment.order_id==Order.id)).mappings().one()
        return {key:(int(val) if key.endswith('count') else format(val,'.2f')) for key,val in row.items()}|dict(currency='INR',platform_revenue='0.00')

    def _notify(self,order,seller,event,title,body):
        from app.services.notifications import publish_event
        for recipient in {order.buyer_id,seller.user_id}:
            publish_event(self.session,recipient,f'payment:{order.id}:{event}','PAYMENT_STATUS','order',order.id,title,body)

    def instructions(self,actor_id,order_id):
        actor=require_user(self.session,actor_id);order,seller=self._owned(actor,order_id)
        payment=self._payment(order_id)
        from app.services.payment_settings import PaymentSettingsService
        service=PaymentSettingsService(self.session,self.settings);row=service.row(seller.id)
        reason=service.reason(row)
        if not payment or payment.method!='UPI':reason='This order has no direct UPI payment method'
        elif reason is None and (payment.destination_revision!=row.revision or payment.destination_upi_id!=row.upi_id or payment.destination_name!=row.account_holder_name):reason='Payment destination changed; contact seller before paying'
        from app.models import User
        seller_user=self.session.get(User,seller.user_id)
        if not seller_user.is_active or seller_user.role!='SELLER':reason='Seller is unavailable'
        if payment and payment.status=='SELLER_CONFIRMED':reason='Seller already confirmed payment receipt'
        if order.status in TERMINAL:reason='This order is cancelled or rejected'
        available=reason is None
        from urllib.parse import urlencode
        uri='upi://pay?'+urlencode(dict(pa=payment.destination_upi_id,pn=payment.destination_name,am=format(order.total_amount,'.2f'),cu='INR',tn=f'Order {order.id}')) if available else None
        return dict(available=available,reason=reason,upi_id=payment.destination_upi_id if available else None,account_holder_name=payment.destination_name if available else None,amount=format(order.total_amount,'.2f'),currency='INR',upi_uri=uri,verification_label='Admin reviewed destination; not bank verified' if available else None)

    def summary(self,actor_id):
        actor=require_user(self.session,actor_id)
        if actor.role not in {'SELLER','ADMIN'}:raise InvalidRole('Seller or admin required')
        rows=self.session.execute(select(Order,OrderPayment).join(SellerProfile,Order.seller_id==SellerProfile.id).outerjoin(OrderPayment,OrderPayment.order_id==Order.id).where(self._scope(actor))).all()
        totals=dict(order_value=Decimal('0.00'),confirmed_collections=Decimal('0.00'),pending_cod_collections=Decimal('0.00'),upi_awaiting_verification=Decimal('0.00'))
        for order,payment in rows:
            totals['order_value']+=order.total_amount
            if payment and payment.status=='SELLER_CONFIRMED':totals['confirmed_collections']+=order.total_amount
            elif payment and order.status not in TERMINAL:
                if payment.method=='COD':totals['pending_cod_collections']+=order.total_amount
                elif payment.status=='BUYER_REPORTED':totals['upi_awaiting_verification']+=order.total_amount
        return {k:format(v,'.2f') for k,v in totals.items()}|dict(currency='INR',platform_revenue='0.00',scope='ALL_OWNED_ORDERS')
