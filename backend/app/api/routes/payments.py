from fastapi import APIRouter, Query
from app.api.contracts import IdentifierPath
from app.api.dependencies import Buyer, Seller, Admin, CurrentUser, TransactionSession
from app.schemas.payment import MethodInput, ReportInput, ConfirmationInput, PaymentPage, PaymentView, PaymentMetrics
from app.services.payments import PaymentService

router=APIRouter(prefix='/payments',tags=['Direct payment records'])


@router.get('',response_model=PaymentPage)
def payments(user:CurrentUser,session:TransactionSession,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    return PaymentService(session).list(user.id,offset=offset,limit=limit)


@router.get('/metrics',response_model=PaymentMetrics)
def metrics(user:Admin,session:TransactionSession):
    return PaymentService(session).metrics(user.id)


@router.get('/orders/{order_id}',response_model=PaymentView)
def payment(order_id:IdentifierPath,user:CurrentUser,session:TransactionSession):
    return PaymentService(session).get(user.id,order_id)


@router.post('/orders/{order_id}/method',response_model=PaymentView)
def record_method(order_id:IdentifierPath,data:MethodInput,user:Buyer,session:TransactionSession):
    return PaymentService(session).record_method(user.id,order_id,data)


@router.post('/orders/{order_id}/report',response_model=PaymentView)
def report(order_id:IdentifierPath,data:ReportInput,user:Buyer,session:TransactionSession):
    return PaymentService(session).report(user.id,order_id,data)


@router.post('/orders/{order_id}/confirm',response_model=PaymentView)
def confirm(order_id:IdentifierPath,data:ConfirmationInput,user:Seller,session:TransactionSession):
    return PaymentService(session).confirm(user.id,order_id,data)
