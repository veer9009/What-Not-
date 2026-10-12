from fastapi import APIRouter

from app.api.contracts import IdentifierPath
from app.api.dependencies import Admin, TransactionSession
from app.schemas.product import ProductRejection, ProductResponse
from app.services.moderation import ModerationService
from app.services.mappers import product_response

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/products/pending", response_model=list[ProductResponse], description='Active database ADMIN only: list pending products.')
def pending_products(user: Admin, session: TransactionSession):
    return [product_response(product) for product in ModerationService(session).list_pending(user.id)]


@router.post("/products/{product_id}/approve", response_model=ProductResponse, description='Active database ADMIN only: approve a pending product.')
def approve_product(product_id: IdentifierPath, user: Admin, session: TransactionSession):
    return product_response(ModerationService(session).approve(user.id, product_id))


@router.post("/products/{product_id}/reject", response_model=ProductResponse, description='Active database ADMIN only: reject a pending product with a reason.')
def reject_product(product_id: IdentifierPath, payload: ProductRejection, user: Admin, session: TransactionSession):
    return product_response(ModerationService(session).reject(user.id, product_id, payload.rejection_reason))
