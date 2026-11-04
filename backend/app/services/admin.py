"""Explicit operator actions with active ADMIN authority and durable audit."""
from datetime import datetime, timezone
from sqlalchemy import select
from app.models import User, Product
from app.models.events import AuditEvent
from app.services.errors import OwnershipError, UserNotFound
from app.services.operations import write_operation
from app.services.users import require_user
from app.services.products import require_product


class AdminService:
    def __init__(self,session): self.session=session

    def _parties(self,actor_id,target_id):
        # Global order prevents two operators taking each other's user locks first.
        users={u.id:u for u in self.session.scalars(select(User).where(User.id.in_([actor_id,target_id]))
            .order_by(User.id).with_for_update().execution_options(populate_existing=True))}
        require_user(self.session,actor_id,role='ADMIN')
        if target_id not in users:raise UserNotFound('Account does not exist')
        return users[target_id]

    @write_operation
    def set_active(self,actor_id,target_id,is_active,reason):
        target=self._parties(actor_id,target_id)
        if target.role=='ADMIN':raise OwnershipError('Admin account status requires the trusted operator process')
        if target.is_active!=is_active:
            target.is_active=is_active
            self.session.add(AuditEvent(actor_id=actor_id,entity_type='user',entity_id=target_id,
                action='USER_REACTIVATED' if is_active else 'USER_SUSPENDED',reason=reason))
        return target

    @write_operation
    def verify(self,actor_id,target_id,channel,reason):
        target=self._parties(actor_id,target_id)
        attribute=f'{channel}_verified_at'
        if channel not in {'phone','email'}:raise OwnershipError('Verification channel is unavailable')
        if getattr(target,attribute) is None:
            setattr(target,attribute,datetime.now(timezone.utc))
            self.session.add(AuditEvent(actor_id=actor_id,entity_type='user',entity_id=target_id,
                action=f'{channel.upper()}_VERIFIED',reason='TRUSTED_BETA_OPERATOR: '+reason))
        return target

    @write_operation
    def takedown_product(self,actor_id,product_id,reason):
        require_user(self.session,actor_id,role='ADMIN',lock=True)
        product=require_product(self.session,product_id,lock=True)
        previous=product.status
        product.status='REJECTED';product.rejection_reason=reason
        self.session.add(AuditEvent(actor_id=actor_id,entity_type='product',entity_id=product_id,
            action='PRODUCT_TAKEDOWN',previous_status=previous,next_status='REJECTED',reason=reason))
        return product
