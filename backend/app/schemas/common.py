from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_BIGINT = 2**63 - 1
DatabaseId = Annotated[int, Field(strict=True, gt=0, le=MAX_BIGINT, description="Positive PostgreSQL BIGINT identifier")]
MAX_INTEGER = 2**31 - 1
MAX_MONEY = Decimal('9999999999.99')
Quantity = Annotated[int, Field(strict=True, gt=0, le=MAX_INTEGER)]
Money = Annotated[Decimal, Field(ge=0, le=MAX_MONEY, decimal_places=2, allow_inf_nan=False)]
Price = Annotated[Decimal, Field(gt=0, le=MAX_MONEY, decimal_places=2, allow_inf_nan=False)]
Name = Annotated[str, Field(min_length=1, max_length=120)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_default=True,
                              revalidate_instances='always')


class HealthResponse(ContractModel):
    status: Literal["ok"] = "ok"
    service: Literal["what-not-api"] = "what-not-api"


class NotImplementedResponse(ContractModel):
    detail: str
