from enum import Enum

from pydantic import Field, model_validator

from .common import ContractModel, DatabaseId, Money, Name, Price, Quantity


class OrderStatus(str, Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderItem(ContractModel):
    product_id: DatabaseId
    quantity: Quantity


class OrderCreate(ContractModel):
    """One seller per request. The future service must resolve product ownership,
    buyer identity, eligibility, stock and prices before creating an order.
    """

    seller_id: DatabaseId
    items: list[OrderItem] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_products(self):
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("Each product may appear only once in an order")
        return self


class OrderItemResponse(OrderItem):
    seller_id: DatabaseId
    name: Name
    unit_price: Price


class OrderResponse(ContractModel):
    id: DatabaseId
    buyer_id: DatabaseId
    seller_id: DatabaseId
    items: list[OrderItemResponse] = Field(min_length=1)
    status: OrderStatus = OrderStatus.PLACED
    subtotal: Money
    delivery_fee: Money
    total: Money

    @model_validator(mode="after")
    def check_seller_and_totals(self):
        if any(item.seller_id != self.seller_id for item in self.items):
            raise ValueError("All order items must belong to the order's seller")
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("Each product may appear only once in an order")
        if self.subtotal != sum(item.unit_price * item.quantity for item in self.items):
            raise ValueError("Subtotal must match the order items")
        if self.total != self.subtotal + self.delivery_fee:
            raise ValueError("Total must equal subtotal plus delivery fee")
        return self


class OrderStatusUpdate(ContractModel):
    """Accepted values only; permissions and lifecycle transitions need a service."""

    status: OrderStatus
