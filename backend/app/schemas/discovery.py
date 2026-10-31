"""Explicit-location reads with a minimal buyer-safe product view."""
from typing import Annotated

from pydantic import Field, model_validator

from app.schemas.common import ContractModel, DatabaseId, Name
from app.schemas.location import Coordinate
from app.schemas.product import ProductCreate


class DiscoverySource(ContractModel):
    address_id: DatabaseId | None = None
    location: Coordinate | None = None

    @model_validator(mode='after')
    def exactly_one_source(self):
        if (self.address_id is None) == (self.location is None):
            raise ValueError('Choose exactly one discovery location source')
        return self


class DiscoveryQuery(DiscoverySource):
    offset: Annotated[int, Field(strict=True, ge=0, le=2147483647)] = 0
    limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 100


class BuyerProduct(ProductCreate):
    id: DatabaseId
    seller_id: DatabaseId
    shop_name: Name
    is_verified: Annotated[bool, Field(strict=True)]
    distance_km: Annotated[float, Field(ge=0, allow_inf_nan=False)]
