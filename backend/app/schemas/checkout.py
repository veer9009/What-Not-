from typing import Literal
from pydantic import Field, model_validator
from app.schemas.common import ContractModel, DatabaseId
from app.schemas.order import OrderItem

class CheckoutGroup(ContractModel):
    seller_id: DatabaseId
    items: list[OrderItem]=Field(min_length=1,max_length=100)
    payment_method: Literal['COD','UPI']|None=None

class CheckoutInput(ContractModel):
    address_id: DatabaseId
    sellers: list[CheckoutGroup]=Field(min_length=1,max_length=50)
    @model_validator(mode='after')
    def unique(self):
        if len({s.seller_id for s in self.sellers})!=len(self.sellers):raise ValueError('Duplicate seller')
        ids=[i.product_id for s in self.sellers for i in s.items]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate product')
        if any(i.expected_unit_price is None for s in self.sellers for i in s.items):raise ValueError('Confirm every current price')
        return self
