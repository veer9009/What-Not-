import pytest
from pydantic import ValidationError

from app.schemas.order import OrderCreate, OrderItem, OrderResponse, OrderStatus, OrderStatusUpdate


def response_data(**changes):
    return {"id": 20, "buyer_id": 1, "seller_id": 2,
            "items": [{"product_id": 10, "seller_id": 2, "name": "Cotton Tote", "quantity": 2, "unit_price": "250.00"}],
            "subtotal": "500.00", "delivery_fee": "49.00", "total": "549.00", **changes}


def test_order_creation_declares_one_seller_and_product_references():
    order = OrderCreate(seller_id=2, items=[{"product_id": 10, "quantity": 2}])
    assert order.seller_id == 2
    assert order.items[0].product_id == 10
    with pytest.raises(ValidationError):
        OrderCreate(seller_id=2, items=[{"product_id": 10, "quantity": 2, "seller_id": 3}])


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, "2"])
def test_quantity_is_a_positive_integer(quantity):
    with pytest.raises(ValidationError):
        OrderItem(product_id=10, quantity=quantity)


@pytest.mark.parametrize("product_id", [0, -1, True, "10", 2**63])
def test_product_id_is_a_positive_bigint(product_id):
    with pytest.raises(ValidationError):
        OrderItem(product_id=product_id, quantity=1)


def test_empty_and_duplicate_order_items_rejected():
    for items in [[], [{"product_id": 10, "quantity": 1}, {"product_id": 10, "quantity": 2}]]:
        with pytest.raises(ValidationError):
            OrderCreate(seller_id=2, items=items)


@pytest.mark.parametrize("field,value", [("buyer_id", 1), ("status", "DELIVERED"), ("total", "0")])
def test_client_cannot_supply_server_order_fields(field, value):
    with pytest.raises(ValidationError):
        OrderCreate(seller_id=2, items=[{"product_id": 10, "quantity": 1}], **{field: value})


@pytest.mark.parametrize("status", ["PLACED", "ACCEPTED", "PREPARING", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED", "REJECTED"])
def test_order_status_values(status):
    assert OrderResponse(**response_data(status=status)).status.value == status
    assert OrderStatusUpdate(status=status).status.value == status


@pytest.mark.parametrize("status", ["placed", "PAID", "UNKNOWN"])
def test_invalid_order_status(status):
    with pytest.raises(ValidationError):
        OrderResponse(**response_data(status=status))


def test_response_defaults_to_placed_and_checks_one_seller_and_totals():
    assert OrderResponse(**response_data()).status == OrderStatus.PLACED
    data = response_data()
    data["items"][0]["seller_id"] = 3
    with pytest.raises(ValidationError):
        OrderResponse(**data)
    for changes in [{"total": "1"}, {"subtotal": "1"}, {"delivery_fee": "-1"}, {"id": "20"}, {"buyer_id": False}]:
        with pytest.raises(ValidationError):
            OrderResponse(**response_data(**changes))
