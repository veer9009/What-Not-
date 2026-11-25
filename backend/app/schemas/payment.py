from datetime import datetime
from typing import Literal
from pydantic import Field
from app.schemas.common import ContractModel, DatabaseId


class MethodInput(ContractModel):
    method: Literal['COD','UPI']


class ReportInput(ContractModel):
    reference: str|None=Field(default=None,min_length=1,max_length=100,pattern=r'^[A-Za-z0-9][A-Za-z0-9 _./-]{0,99}$')


class ConfirmationInput(ContractModel):
    expected_status: Literal['PENDING','BUYER_REPORTED']


class PaymentView(ContractModel):
    order_id: DatabaseId
    seller_id: DatabaseId
    seller_name: str
    amount: str
    currency: Literal['INR']='INR'
    order_status: str
    order_date: datetime
    method: Literal['COD','UPI']|None
    status: Literal['NOT_RECORDED','PENDING','BUYER_REPORTED','SELLER_CONFIRMED']
    reference: str|None
    reported_at: datetime|None
    confirmed_at: datetime|None
    can_select_method: bool
    can_report: bool
    can_confirm: bool


class PaymentPage(ContractModel):
    items: list[PaymentView]
    has_more: bool


class PaymentMetrics(ContractModel):
    currency: Literal['INR']='INR'
    order_count: int
    order_value: str
    cod_order_value: str
    upi_order_value: str
    unrecorded_order_value: str
    buyer_reported_count: int
    buyer_reported_value: str
    seller_confirmed_count: int
    seller_confirmed_value: str
    pending_confirmation_count: int
    cancelled_order_value: str
    cancelled_confirmed_value: str
    platform_revenue: str
