from typing import Literal

from pydantic import EmailStr, Field, SecretStr

from .common import ContractModel, Name


class UserRegistration(ContractModel):
    name: Name
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
    role: Literal["BUYER", "SELLER"] = "BUYER"


class LoginRequest(ContractModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)
