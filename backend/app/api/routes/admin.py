from fastapi import APIRouter, Query, Request
from sqlalchemy import select, func

from app.api.contracts import IdentifierPath
from app.api.dependencies import Admin, TransactionSession
from app.schemas.product import ProductRejection, ProductResponse, ProductApproval
from app.services.moderation import ModerationService
from app.services.mappers import product_response
from app.services.mappers import order_response
from app.models import User, Order
from app.models.events import AuditEvent, EmailOutbox
from app.services.admin import AdminService
from app.services.orders import OrderService
from app.schemas.admin import AccountAction, VerificationAction, Investigation, OrderResolution
from app.schemas.order import OrderStatus, OrderResponse, FulfillmentResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/products/pending", response_model=list[ProductResponse], description='Active database ADMIN only: list pending products.')
def pending_products(user: Admin, session: TransactionSession, offset:int=Query(0,ge=0), limit:int=Query(50,ge=1,le=100)):
    return [product_response(product) for product in ModerationService(session).list_pending(user.id,offset=offset,limit=limit)]


@router.post("/products/{product_id}/approve", response_model=ProductResponse, description='Active database ADMIN only: approve a pending product.')
def approve_product(product_id: IdentifierPath, payload:ProductApproval, user: Admin, session: TransactionSession):
    return product_response(ModerationService(session).approve(user.id, product_id,payload.expected_updated_at))


@router.post("/products/{product_id}/reject", response_model=ProductResponse, description='Active database ADMIN only: reject a pending product with a reason.')
def reject_product(product_id: IdentifierPath, payload: ProductRejection, user: Admin, session: TransactionSession):
    return product_response(ModerationService(session).reject(user.id, product_id, payload.rejection_reason))


def account(user):
    return dict(id=user.id,name=user.name,email=user.email,phone=user.phone,role=user.role,
        is_active=user.is_active,phone_verified_at=user.phone_verified_at,email_verified_at=user.email_verified_at)


@router.get('/users')
def users(user:Admin,session:TransactionSession,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    return [account(row) for row in session.scalars(select(User).order_by(User.id.desc()).offset(offset).limit(limit))]


@router.patch('/users/{user_id}/active')
def user_active(user_id:IdentifierPath,data:AccountAction,user:Admin,session:TransactionSession):
    return account(AdminService(session).set_active(user.id,user_id,data.is_active,data.reason))


@router.post('/users/{user_id}/verify')
def verify_user(user_id:IdentifierPath,data:VerificationAction,user:Admin,session:TransactionSession):
    return account(AdminService(session).verify(user.id,user_id,data.channel,data.reason))


@router.get('/orders',response_model=list[OrderResponse])
def orders(user:Admin,session:TransactionSession,status:OrderStatus|None=None,
           offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    query=select(Order)
    if status is not None:query=query.where(Order.status==status.value)
    return [order_response(row) for row in session.scalars(query.order_by(Order.id.desc()).offset(offset).limit(limit))]


@router.post('/orders/{order_id}/resolve',response_model=OrderResponse)
def resolve_order(order_id:IdentifierPath,data:OrderResolution,user:Admin,session:TransactionSession):
    return order_response(OrderService(session).admin_resolve(user.id,order_id,data.action,data.reason))


@router.post('/orders/{order_id}/fulfillment',response_model=FulfillmentResponse)
def investigate_delivery(order_id:IdentifierPath,data:Investigation,user:Admin,session:TransactionSession):
    return OrderService(session).fulfillment(user.id,order_id,data.reason)


@router.post('/products/{product_id}/takedown',response_model=ProductResponse)
def takedown(product_id:IdentifierPath,data:Investigation,user:Admin,session:TransactionSession):
    return product_response(AdminService(session).takedown_product(user.id,product_id,data.reason))


@router.get('/audit')
def audit(user:Admin,session:TransactionSession,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    return [dict(id=row.id,actor_id=row.actor_id,actor_type=row.actor_type,entity_type=row.entity_type,
                 entity_id=row.entity_id,action=row.action,previous_status=row.previous_status,
                 next_status=row.next_status,reason=row.reason,created_at=row.created_at)
            for row in session.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).offset(offset).limit(limit))]


@router.get('/operations')
def operations(user:Admin,session:TransactionSession,request:Request):
    counts=dict(session.execute(select(EmailOutbox.state,func.count()).group_by(EmailOutbox.state)).all())
    oldest=session.scalar(select(func.min(EmailOutbox.created_at)).where(EmailOutbox.state.in_(['PENDING','LEASED'])))
    return dict(email_provider_enabled=request.app.state.settings.email_provider!='disabled',
                outbox_counts=counts,oldest_pending_at=oldest)
