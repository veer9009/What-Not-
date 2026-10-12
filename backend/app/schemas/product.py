from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, model_validator

from .common import ContractModel, DatabaseId, MAX_INTEGER, Name, Price

Description = Annotated[str, Field(min_length=1, max_length=5000)]
Stock = Annotated[int, Field(strict=True, ge=0, le=MAX_INTEGER)]
DeliveryRadius = Literal[1, 2, 3]
RejectionReason = Annotated[str, Field(min_length=1, max_length=2000)]


class ProductStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProductCategory(str, Enum):
    HANDMADE = "Handmade"
    HOME_DECOR = "Home Decor"
    GIFTS = "Gifts"
    FASHION = "Fashion"
    JEWELLERY = "Jewellery"
    CRAFTS = "Crafts"


class ProductCreate(ContractModel):
    """Seller identity and PENDING status will be assigned by the future service."""

    name: Name
    description: Description
    price: Price
    stock_quantity: Stock
    category: ProductCategory
    delivery_radius_km: DeliveryRadius
    image_url: HttpUrl | None = None

    @model_validator(mode="before")
    @classmethod
    def require_integer_radius(cls, data):
        # Literal values must not accept bool or float values equal to an integer.
        if isinstance(data, dict) and "delivery_radius_km" in data and type(data["delivery_radius_km"]) is not int:
            raise ValueError("delivery_radius_km must be the integer 1, 2 or 3")
        return data


class ProductUpdate(ContractModel):
    """PATCH: omitted fields remain unchanged; only image_url can be cleared."""

    name: Name | None = None
    description: Description | None = None
    price: Price | None = None
    stock_quantity: Stock | None = None
    category: ProductCategory | None = None
    delivery_radius_km: DeliveryRadius | None = None
    image_url: HttpUrl | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_patch(cls, data):
        if isinstance(data, dict):
            if not data:
                raise ValueError("Provide at least one product field to update")
            if any(value is None for name, value in data.items() if name != "image_url"):
                raise ValueError("Product fields cannot be null except image_url")
            if "delivery_radius_km" in data and type(data["delivery_radius_km"]) is not int:
                raise ValueError("delivery_radius_km must be the integer 1, 2 or 3")
        return data


class ProductResponse(ProductCreate):
    id: DatabaseId
    seller_id: DatabaseId
    status: ProductStatus = ProductStatus.PENDING
    rejection_reason: RejectionReason | None = None
    is_active: Annotated[bool, Field(strict=True)] = True

    @model_validator(mode="after")
    def check_rejection_reason(self):
        if self.status == ProductStatus.REJECTED and not self.rejection_reason:
            raise ValueError("Rejected products require a rejection reason")
        if self.status != ProductStatus.REJECTED and self.rejection_reason is not None:
            raise ValueError("Only rejected products may have a rejection reason")
        return self


class ProductRejection(ContractModel):
    rejection_reason: RejectionReason


class ProductActivation(ContractModel):
    is_active: Annotated[bool, Field(strict=True)]
