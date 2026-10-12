from fastapi import APIRouter

from app.api.contracts import IdentifierPath, PLACEHOLDER_DESCRIPTION, PLACEHOLDER_RESPONSES, not_implemented
from app.schemas.product import ProductActivation, ProductCreate, ProductResponse, ProductUpdate
from app.api.dependencies import Seller, TransactionSession, current_seller_profile
from app.services.products import ProductService
from app.services.mappers import product_response

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=list[ProductResponse], description=PLACEHOLDER_DESCRIPTION, responses=PLACEHOLDER_RESPONSES)
async def list_products() -> list[ProductResponse]:
    not_implemented()


@router.post("", response_model=ProductResponse, status_code=201, description='Create a PENDING product for the authenticated seller profile.')
def create_product(payload: ProductCreate, user: Seller, session: TransactionSession):
    profile = current_seller_profile(session, user.id)
    return product_response(ProductService(session).create(user.id, profile.id, payload))


@router.get("/{product_id}", response_model=ProductResponse, description=PLACEHOLDER_DESCRIPTION, responses=PLACEHOLDER_RESPONSES)
async def get_product(product_id: IdentifierPath) -> ProductResponse:
    not_implemented()


@router.patch("/{product_id}", response_model=ProductResponse, description='Edit only an owned seller product. Approved edits return to PENDING.')
def update_product(product_id: IdentifierPath, payload: ProductUpdate, user: Seller, session: TransactionSession):
    return product_response(ProductService(session).update(user.id, product_id, payload))


@router.patch("/{product_id}/activation", response_model=ProductResponse, description='Activate/deactivate only an owned seller product.')
def set_product_active(product_id: IdentifierPath, payload: ProductActivation, user: Seller, session: TransactionSession):
    return product_response(ProductService(session).set_active(user.id, product_id, payload.is_active))


@router.post("/{product_id}/resubmit", response_model=ProductResponse, description='Resubmit only an owned rejected product.')
def resubmit_product(product_id: IdentifierPath, user: Seller, session: TransactionSession):
    return product_response(ProductService(session).resubmit(user.id, product_id))
