from typing import Literal

from pydantic import EmailStr, Field, SecretStr, field_validator

from .common import ContractModel, Name
from .user import PublicUserResponse


class UserRegistration(ContractModel):
    name: Name
    email: EmailStr = Field(max_length=320)
    phone: str = Field(min_length=1, max_length=32)
    password: SecretStr = Field(min_length=8, max_length=128)
    role: Literal["BUYER", "SELLER"] = "BUYER"

    @field_validator('password', mode='before')
    @classmethod
    def preserve_password(cls, value):
        # SecretStr's string schema otherwise inherits whitespace stripping.
        return SecretStr(value) if isinstance(value, str) else value

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class LoginRequest(ContractModel):
    email: EmailStr = Field(max_length=320)
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator('password', mode='before')
    @classmethod
    def preserve_password(cls, value):
        return SecretStr(value) if isinstance(value, str) else value

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class TokenResponse(ContractModel):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'
    expires_in: int = Field(gt=0)
    user: PublicUserResponse
