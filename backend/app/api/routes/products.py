from fastapi import APIRouter

from app.api.contracts import IdentifierPath, PLACEHOLDER_DESCRIPTION, PLACEHOLDER_RESPONSES, not_implemented
from app.schemas.product import ProductActivation, ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"], responses=PLACEHOLDER_RESPONSES)


@router.get("", response_model=list[ProductResponse], description=PLACEHOLDER_DESCRIPTION)
async def list_products() -> list[ProductResponse]:
    not_implemented()


@router.post("", response_model=ProductResponse, status_code=201, description=PLACEHOLDER_DESCRIPTION)
async def create_product(payload: ProductCreate) -> ProductResponse:
    not_implemented()


@router.get("/{product_id}", response_model=ProductResponse, description=PLACEHOLDER_DESCRIPTION)
async def get_product(product_id: IdentifierPath) -> ProductResponse:
    not_implemented()


@router.patch("/{product_id}", response_model=ProductResponse, description=PLACEHOLDER_DESCRIPTION)
async def update_product(product_id: IdentifierPath, payload: ProductUpdate) -> ProductResponse:
    not_implemented()


@router.patch("/{product_id}/activation", response_model=ProductResponse, description=PLACEHOLDER_DESCRIPTION)
async def set_product_active(product_id: IdentifierPath, payload: ProductActivation) -> ProductResponse:
    not_implemented()


@router.post("/{product_id}/resubmit", response_model=ProductResponse, description=PLACEHOLDER_DESCRIPTION)
async def resubmit_product(product_id: IdentifierPath) -> ProductResponse:
    not_implemented()
