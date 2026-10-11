from enum import Enum

from pydantic import EmailStr

from .common import ContractModel, DatabaseId, Name


class UserRole(str, Enum):
    BUYER = "BUYER"
    SELLER = "SELLER"
    ADMIN = "ADMIN"


class PublicUserResponse(ContractModel):
    id: DatabaseId
    name: Name
    email: EmailStr
    role: UserRole
