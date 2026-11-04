from typing import Literal
from pydantic import Field
from app.schemas.common import ContractModel


class Investigation(ContractModel):
    reason:str=Field(min_length=1,max_length=1000)


class AccountAction(Investigation):
    is_active:bool=Field(strict=True)


class VerificationAction(Investigation):
    channel:Literal['phone','email']


class OrderResolution(Investigation):
    action:Literal['COMPLETE_DISPUTE','CANCEL_DISPUTE','CANCEL_STRANDED','CANCEL_INVESTIGATED']
