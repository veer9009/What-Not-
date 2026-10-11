from fastapi import APIRouter

from app.api.contracts import IdentifierPath, PLACEHOLDER_DESCRIPTION, PLACEHOLDER_RESPONSES, not_implemented
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["Orders"], responses=PLACEHOLDER_RESPONSES)


@router.get("", response_model=list[OrderResponse], description=PLACEHOLDER_DESCRIPTION)
async def list_orders() -> list[OrderResponse]:
    not_implemented()


@router.post("", response_model=OrderResponse, status_code=201, description=PLACEHOLDER_DESCRIPTION)
async def create_order(payload: OrderCreate) -> OrderResponse:
    not_implemented()


@router.get("/{order_id}", response_model=OrderResponse, description=PLACEHOLDER_DESCRIPTION)
async def get_order(order_id: IdentifierPath) -> OrderResponse:
    not_implemented()


@router.patch("/{order_id}/status", response_model=OrderResponse, description=PLACEHOLDER_DESCRIPTION)
async def update_order_status(order_id: IdentifierPath, payload: OrderStatusUpdate) -> OrderResponse:
    not_implemented()
