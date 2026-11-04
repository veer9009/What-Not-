from sqlalchemy.orm import Session

from app.repositories.products import ProductRepository
from app.schemas.product import ProductRejection
from app.services.errors import InvalidProductTransition
from app.services.operations import write_operation
from app.services.products import require_product
from app.services.users import pagination, require_user
from app.models.events import AuditEvent


class ModerationService:
    def __init__(self, session: Session):
        self.session = session

    def list_pending(self, admin_id: int, *, offset=0, limit=100):
        require_user(self.session, admin_id, role='ADMIN')
        return ProductRepository(self.session).pending(*pagination(offset, limit))

    def _pending_locked(self, admin_id, product_id):
        require_user(self.session, admin_id, role='ADMIN', lock=True)
        product = require_product(self.session, product_id, lock=True)
        if product.status != 'PENDING':
            raise InvalidProductTransition('Only pending products can be moderated')
        return product

    @write_operation
    def approve(self, admin_id: int, product_id: int, expected_updated_at=None):
        product = self._pending_locked(admin_id, product_id)
        if expected_updated_at is not None and product.updated_at != expected_updated_at:
            raise InvalidProductTransition('Listing changed after review; refresh before approving')
        product.status, product.rejection_reason = 'APPROVED', None
        self.session.add(AuditEvent(actor_id=admin_id,entity_type='product',entity_id=product.id,
            action='PRODUCT_APPROVED',previous_status='PENDING',next_status='APPROVED'))
        return product

    @write_operation
    def reject(self, admin_id: int, product_id: int, reason: str):
        reason = ProductRejection(rejection_reason=reason).rejection_reason
        product = self._pending_locked(admin_id, product_id)
        product.status, product.rejection_reason = 'REJECTED', reason
        self.session.add(AuditEvent(actor_id=admin_id,entity_type='product',entity_id=product.id,
            action='PRODUCT_REJECTED',previous_status='PENDING',next_status='REJECTED',reason=reason))
        return product
