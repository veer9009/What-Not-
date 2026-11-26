from datetime import datetime
from typing import Literal
from pydantic import Field
from sqlalchemy import select
from app.schemas.common import ContractModel
from app.models.shopping import SellerPaymentSettings
from app.models.events import AuditEvent
from app.core.config import Settings
from app.services.users import require_user
from app.services.sellers import owned_seller
from app.services.errors import PersistenceConflict, SellerNotFound
from app.services.operations import write_operation

class SettingsInput(ContractModel):
    upi_id: str|None=Field(default=None,max_length=255,pattern=r'^[A-Za-z0-9._-]{2,128}@[A-Za-z0-9.-]{2,64}$')
    account_holder_name: str|None=Field(default=None,min_length=1,max_length=120)
    accept_cod: bool=True
    accept_upi: bool=False

class ReviewInput(ContractModel):
    status: Literal['APPROVED','REJECTED']
    expected_updated_at: datetime
    reason: str=Field(min_length=1,max_length=1200)

class PaymentSettingsService:
    def __init__(self,session,settings=None):self.session=session;self.settings=settings or Settings(_env_file=None)
    def row(self,seller_id,lock=False):
        query=select(SellerPaymentSettings).where(SellerPaymentSettings.seller_id==seller_id)
        if lock:query=query.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(query)
    def reason(self,row):
        if not self.settings.prepaid_upi_enabled:return 'Prepaid UPI is disabled pending approved refund policy'
        if not self.settings.approved_refund_policy_reference:return 'Approved refund policy is required'
        if not row or not row.accept_upi:return 'Seller does not accept UPI'
        if row.verification_status!='APPROVED' or not row.upi_id or not row.account_holder_name:return 'Seller payment destination requires admin review'
        return None
    def view(self,row,seller_id):
        reason=self.reason(row)
        return dict(seller_id=str(seller_id),upi_id=row.upi_id if row else None,account_holder_name=row.account_holder_name if row else None,
            accept_cod=row.accept_cod if row else True,accept_upi=row.accept_upi if row else False,verification_status=row.verification_status if row else 'PENDING',
            updated_at=row.updated_at if row else None,revision=row.revision if row else 0,review_reason=row.review_reason if row else None,
            upi_enabled=reason is None,upi_unavailable_reason=reason)
    def get(self,actor_id):
        actor=require_user(self.session,actor_id,role='SELLER')
        from app.models import SellerProfile
        seller=self.session.scalar(select(SellerProfile).where(SellerProfile.user_id==actor.id))
        if seller is None:raise SellerNotFound('Seller profile does not exist')
        owned_seller(self.session,actor_id,seller.id)
        return self.view(self.row(seller.id),seller.id)
    @write_operation
    def put(self,actor_id,data):
        data=SettingsInput.model_validate(data)
        actor=require_user(self.session,actor_id,role='SELLER',lock=True)
        from app.models import SellerProfile
        seller=self.session.scalar(select(SellerProfile).where(SellerProfile.user_id==actor.id))
        if seller is None:raise SellerNotFound('Seller profile does not exist')
        owned_seller(self.session,actor_id,seller.id)
        row=self.row(seller.id,True)
        if row is None:row=SellerPaymentSettings(seller_id=seller.id);self.session.add(row)
        elif all(getattr(row,k)==v for k,v in data.model_dump().items()):return self.view(row,seller.id)
        else:row.revision+=1
        for key,value in data.model_dump().items():setattr(row,key,value)
        row.verification_status='PENDING';row.review_reason=None
        self.session.add(AuditEvent(actor_id=actor.id,entity_type='seller_payment_settings',entity_id=seller.id,action='PAYMENT_DESTINATION_CHANGED',next_status='PENDING',reason='Destination requires manual admin review'))
        self.session.flush();self.session.refresh(row)
        return self.view(row,seller.id)
    def list(self,actor_id):
        require_user(self.session,actor_id,role='ADMIN')
        return dict(items=[self.view(r,r.seller_id) for r in self.session.scalars(select(SellerPaymentSettings).order_by(SellerPaymentSettings.seller_id))])
    @write_operation
    def review(self,actor_id,seller_id,data):
        data=ReviewInput.model_validate(data);require_user(self.session,actor_id,role='ADMIN',lock=True)
        row=self.row(seller_id,True)
        if row is None or row.updated_at!=data.expected_updated_at:raise PersistenceConflict('Payment details changed; refresh before review')
        if data.status=='APPROVED' and (not row.upi_id or not row.account_holder_name):raise PersistenceConflict('Complete destination details are required')
        previous=row.verification_status;row.verification_status=data.status;row.review_reason=data.reason
        self.session.add(AuditEvent(actor_id=actor_id,entity_type='seller_payment_settings',entity_id=seller_id,action='PAYMENT_DESTINATION_REVIEWED',previous_status=previous,next_status=data.status,reason=data.reason))
        self.session.flush();self.session.refresh(row)
        return self.view(row,seller_id)
