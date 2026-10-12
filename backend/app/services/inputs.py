"""Internal service inputs, never public registration or authentication contracts."""
import re
from decimal import Decimal
from typing import Annotated, ClassVar

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator

from app.schemas.common import ContractModel, DatabaseId, Name
from app.schemas.order import OrderCreate
from app.schemas.user import UserRole

Phone = Annotated[str, Field(min_length=1, max_length=32)]
Latitude = Annotated[Decimal, Field(ge=-90, le=90, decimal_places=6, allow_inf_nan=False)]
Longitude = Annotated[Decimal, Field(ge=-180, le=180, decimal_places=6, allow_inf_nan=False)]
StrictBool = Annotated[bool, Field(strict=True)]


class UserCreate(ContractModel):
    name: Name
    email: Annotated[EmailStr, Field(max_length=320)]
    phone: Phone
    password_hash: SecretStr = Field(min_length=1, max_length=255, repr=False, exclude=True)
    role: UserRole
    is_active: StrictBool = True

    @field_validator('password_hash')
    @classmethod
    def encoded_hash(cls, value):
        encoded = value.get_secret_value()
        bcrypt = r'\$2[aby]\$(?:0[4-9]|[12][0-9]|3[01])\$[./A-Za-z0-9]{53}'
        argon2 = r'\$argon2id\$v=19\$m=[1-9][0-9]*,t=[1-9][0-9]*,p=[1-9][0-9]*\$[A-Za-z0-9+/]{8,}\$[A-Za-z0-9+/]{16,}'
        if not (re.fullmatch(bcrypt, encoded) or re.fullmatch(argon2, encoded)):
            raise ValueError('Provide a precomputed bcrypt or Argon2id encoded hash')
        return value


class PatchInput(ContractModel):
    nullable_fields: ClassVar[set[str]] = set()

    @model_validator(mode='before')
    @classmethod
    def valid_patch(cls, data):
        if isinstance(data, dict):
            if not data:
                raise ValueError('Provide at least one field to update')
            if any(value is None for key, value in data.items() if key not in cls.nullable_fields):
                raise ValueError('This field cannot be null')
        return data


class SellerCreate(ContractModel):
    shop_name: Name
    description: Annotated[str, Field(min_length=1, max_length=5000)] | None = None
    phone: Phone
    latitude: Latitude
    longitude: Longitude


class SellerUpdate(PatchInput):
    nullable_fields = {'description'}
    shop_name: Name | None = None
    description: Annotated[str, Field(min_length=1, max_length=5000)] | None = None
    phone: Phone | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None


class AddressCreate(ContractModel):
    label: Annotated[str, Field(min_length=1, max_length=80)]
    address_line1: Annotated[str, Field(min_length=1, max_length=255)]
    address_line2: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    city: Name
    state: Name
    pincode: Annotated[str, Field(min_length=1, max_length=20)]
    latitude: Latitude
    longitude: Longitude
    is_default: StrictBool = False


class AddressUpdate(PatchInput):
    nullable_fields = {'address_line2'}
    label: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    address_line1: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    address_line2: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    city: Name | None = None
    state: Name | None = None
    pincode: Annotated[str, Field(min_length=1, max_length=20)] | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    is_default: StrictBool | None = None


class OrderPlacement(OrderCreate):
    buyer_id: DatabaseId
    address_id: DatabaseId
