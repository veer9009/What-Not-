from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, ProductStatus,
    ProductRejection, ProductActivation,
)


def product_data(**changes):
    return dict(name="Cotton Tote", description="Handwoven cotton bag", price="250.00",
                stock_quantity=4, category="Fashion", delivery_radius_km=2, **changes)


def response_data(**changes):
    data = {**product_data(), "id": 10, "seller_id": 2}
    return {**data, **changes}


@pytest.mark.parametrize("radius", [1, 2, 3])
def test_allowed_delivery_radius(radius):
    data = product_data()
    data["delivery_radius_km"] = radius
    assert ProductCreate(**data).delivery_radius_km == radius


@pytest.mark.parametrize("radius", [0, 4, -1, 1.5, True, "2"])
def test_invalid_delivery_radius(radius):
    data = product_data()
    data["delivery_radius_km"] = radius
    with pytest.raises(ValidationError):
        ProductCreate(**data)


def test_new_response_defaults_to_pending_and_active():
    product = ProductResponse(**response_data())
    assert product.status == ProductStatus.PENDING
    assert product.is_active is True
    assert product.rejection_reason is None
    assert product.price == Decimal("250.00")


@pytest.mark.parametrize("status", ["PENDING", "APPROVED", "REJECTED"])
def test_product_status_values(status):
    data = response_data(status=status)
    if status == "REJECTED":
        data["rejection_reason"] = "Please upload a clearer image"
    assert ProductResponse(**data).status.value == status


@pytest.mark.parametrize("field,value", [("status", "approved"), ("status", "LIVE"),
    ("id", "10"), ("seller_id", True), ("id", 0), ("seller_id", -1), ("id", 2**63)])
def test_response_rejects_invalid_status_and_ids(field, value):
    with pytest.raises(ValidationError):
        ProductResponse(**response_data(**{field: value}))


@pytest.mark.parametrize("schema", [ProductCreate, ProductUpdate])
@pytest.mark.parametrize("field,value", [("status", "APPROVED"), ("seller_id", 2),
    ("id", 10), ("rejection_reason", "ignored"), ("is_active", False)])
def test_seller_payload_cannot_set_server_or_moderation_fields(schema, field, value):
    data = product_data() if schema is ProductCreate else {"name": "New name"}
    with pytest.raises(ValidationError):
        schema(**{**data, field: value})


@pytest.mark.parametrize("field,value", [("name", "  "), ("description", ""), ("price", "0"),
    ("price", "-1"), ("price", "NaN"), ("price", "Infinity"), ("price", "1.001"),
    ("stock_quantity", -1), ("stock_quantity", 1.5), ("stock_quantity", True),
    ("category", "Unknown")])
def test_invalid_product_fields(field, value):
    data = product_data()
    data[field] = value
    with pytest.raises(ValidationError):
        ProductCreate(**data)


def test_partial_update_omits_unset_fields_but_rejects_empty_and_null():
    assert ProductUpdate(stock_quantity=0).model_dump(exclude_unset=True) == {"stock_quantity": 0}
    for data in [{}, {"name": None}, {"price": None}, {"stock_quantity": None}]:
        with pytest.raises(ValidationError):
            ProductUpdate(**data)


@pytest.mark.parametrize("reason", ["", "  ", None])
def test_rejection_requires_reason(reason):
    with pytest.raises(ValidationError):
        ProductRejection(rejection_reason=reason)
    with pytest.raises(ValidationError):
        ProductResponse(**response_data(status="REJECTED", rejection_reason=reason))


def test_reason_is_trimmed_and_not_allowed_for_non_rejected_products():
    assert ProductRejection(rejection_reason="  Clearer photo please  ").rejection_reason == "Clearer photo please"
    with pytest.raises(ValidationError):
        ProductResponse(**response_data(status="APPROVED", rejection_reason="Old reason"))


def test_activation_requires_boolean():
    assert ProductActivation(is_active=False).is_active is False
    with pytest.raises(ValidationError):
        ProductActivation(is_active="false")
