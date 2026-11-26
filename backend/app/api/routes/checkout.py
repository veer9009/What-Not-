from typing import Annotated
from fastapi import APIRouter, Header, Request
from pydantic import UUID4
from app.api.dependencies import Buyer, TransactionSession
from app.schemas.checkout import CheckoutInput
from app.services.checkout import CheckoutService
router=APIRouter(prefix='/checkout',tags=['Checkout'])
@router.post('/preview')
def preview(data:CheckoutInput,user:Buyer,session:TransactionSession,request:Request):
    return CheckoutService(session,request.app.state.settings).preview(user.id,data)
@router.post('',status_code=201)
def create(data:CheckoutInput,user:Buyer,session:TransactionSession,request:Request,idempotency_key:Annotated[UUID4,Header(alias='Idempotency-Key')]):
    return CheckoutService(session,request.app.state.settings).create(user.id,data,idempotency_key)
