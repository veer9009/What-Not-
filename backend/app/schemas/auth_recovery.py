from pydantic import EmailStr, Field, SecretStr, field_validator
from app.schemas.common import ContractModel


class RecoveryRequest(ContractModel):
    email: EmailStr = Field(max_length=320)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class RecoveryVerify(ContractModel):
    challenge: str = Field(min_length=1, max_length=128)
    otp: SecretStr = Field(min_length=1, max_length=128)


class RecoveryReset(ContractModel):
    reset_token: SecretStr = Field(min_length=1, max_length=128)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator('password', mode='before')
    @classmethod
    def preserve_password(cls, value):
        return SecretStr(value) if isinstance(value, str) else value
