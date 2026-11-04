from typing import Literal
from datetime import datetime
from uuid import UUID
from pydantic import Field, HttpUrl, AwareDatetime, model_validator
from app.schemas.common import ContractModel, Price

Category = Literal['Video Editing','Travel Video Editing','Influencer Reel Editing','VFX']

class ProviderInput(ContractModel):
    display_name: str = Field(min_length=1, max_length=120)
    bio: str = Field(min_length=1, max_length=5000)

class ListingInput(ContractModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    category: Category
    pricing: Literal['FIXED', 'STARTING', 'HOURLY', 'QUOTATION']
    amount: Price | None = None
    currency: Literal['INR'] = 'INR'
    remote: bool = Field(strict=True)
    locality: str | None = Field(default=None, min_length=1, max_length=160)
    portfolio: list[HttpUrl] = Field(default_factory=list, max_length=12)
    is_active: bool = Field(default=True, strict=True)

    @model_validator(mode='after')
    def requirements(self):
        if (self.pricing == 'QUOTATION') != (self.amount is None):
            raise ValueError('Quotation requires no advertised amount; other pricing requires an amount')
        if not self.remote and not self.locality:
            raise ValueError('Local service requires an explicit locality')
        if any(url.username or url.password for url in self.portfolio):
            raise ValueError('Portfolio links cannot contain credentials')
        return self

class ModerationInput(ContractModel):
    status: Literal['APPROVED', 'REJECTED', 'TAKEN_DOWN']
    reason: str | None = Field(default=None, min_length=1, max_length=1000)
    expected_updated_at: AwareDatetime | None = None

    @model_validator(mode='after')
    def reason_required(self):
        if self.status == 'APPROVED' and self.expected_updated_at is None:
            raise ValueError('Approval requires the reviewed listing timestamp')
        if self.status != 'APPROVED' and not self.reason:
            raise ValueError('A reason is required')
        return self

class RFQInput(ContractModel):
    request_key: UUID
    brief: str = Field(min_length=1, max_length=5000)

class ResponseInput(ContractModel):
    request_key: UUID
    terms: str = Field(min_length=1, max_length=5000)
    amount: Price
    currency: Literal['INR'] = 'INR'

class ReviewInput(ContractModel):
    rating: int = Field(strict=True, ge=1, le=5)
    text: str = Field(min_length=1, max_length=2000)
