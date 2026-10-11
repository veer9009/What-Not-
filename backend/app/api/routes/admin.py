from fastapi import APIRouter

from app.api.contracts import IdentifierPath, PLACEHOLDER_DESCRIPTION, PLACEHOLDER_RESPONSES, not_implemented
from app.schemas.product import ProductRejection, ProductResponse

router = APIRouter(prefix="/admin", tags=["Admin"], responses=PLACEHOLDER_RESPONSES)


@router.get("/products/pending", response_model=list[ProductResponse], description=PLACEHOLDER_DESCRIPTION)
async def pending_products() -> list[ProductResponse]:
    not_implemented()


@router.post("/products/{product_id}/approve", response_model=ProductResponse, description=PLACEHOLDER_DESCRIPTION)
async def approve_product(product_id: IdentifierPath) -> ProductResponse:
    not_implemented()


@router.post("/products/{product_id}/reject", response_model=ProductResponse, description=PLACEHOLDER_DESCRIPTION)
async def reject_product(product_id: IdentifierPath, payload: ProductRejection) -> ProductResponse:
    not_implemented()
