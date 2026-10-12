from fastapi import APIRouter

from app.api.contracts import IdentifierPath, PLACEHOLDER_DESCRIPTION, PLACEHOLDER_RESPONSES, not_implemented
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.api.dependencies import OrderActor, TransactionSession, current_seller_profile
from app.services.orders import OrderService
from app.services.mappers import order_response

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=list[OrderResponse], description='List orders owned by the authenticated buyer or seller.')
def list_orders(user: OrderActor, session: TransactionSession):
    service = OrderService(session)
    if user.role == 'BUYER':
        orders = service.list_for_buyer(user.id)
    else:
        orders = service.list_for_seller(user.id, current_seller_profile(session, user.id).id)
    return [order_response(order) for order in orders]


@router.post("", response_model=OrderResponse, status_code=201, description=PLACEHOLDER_DESCRIPTION, responses=PLACEHOLDER_RESPONSES)
async def create_order(payload: OrderCreate) -> OrderResponse:
    not_implemented()


@router.get("/{order_id}", response_model=OrderResponse, description='Read an order only as its owning buyer or seller.')
def get_order(order_id: IdentifierPath, user: OrderActor, session: TransactionSession):
    return order_response(OrderService(session).get(user.id, order_id))


@router.patch("/{order_id}/status", response_model=OrderResponse, description='Owning buyers may cancel eligible orders; owning sellers may perform supported transitions.')
def update_order_status(order_id: IdentifierPath, payload: OrderStatusUpdate, user: OrderActor, session: TransactionSession):
    return order_response(OrderService(session).transition(user.id, order_id, payload.status))
