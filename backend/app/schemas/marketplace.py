"""Explicit safe address/profile views. No identity fields accepted on writes."""
from datetime import datetime, timezone
from pydantic import field_validator
from app.schemas.common import DatabaseId
from app.services.inputs import AddressCreate, SellerCreate, StrictBool


class AddressResponse(AddressCreate):
    id: DatabaseId
    user_id: DatabaseId


class SellerResponse(SellerCreate):
    id: DatabaseId
    user_id: DatabaseId
    is_verified: StrictBool
    dispatch_location_confirmed_at: datetime | None

    @field_validator('dispatch_location_confirmed_at')
    @classmethod
    def utc_confirmation(cls, value):
        return value.astimezone(timezone.utc) if value is not None else None


def address_response(address):
    return AddressResponse(id=address.id, user_id=address.user_id,
                           **{name: getattr(address, name) for name in AddressCreate.model_fields})


def seller_response(seller):
    return SellerResponse(id=seller.id, user_id=seller.user_id, is_verified=seller.is_verified,
                          dispatch_location_confirmed_at=seller.dispatch_location_confirmed_at,
                          **{name: getattr(seller, name) for name in SellerCreate.model_fields})
