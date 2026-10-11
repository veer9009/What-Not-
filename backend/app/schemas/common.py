from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_BIGINT = 2**63 - 1
DatabaseId = Annotated[int, Field(strict=True, gt=0, le=MAX_BIGINT, description="Positive PostgreSQL BIGINT identifier")]
Quantity = Annotated[int, Field(strict=True, gt=0)]
Money = Annotated[Decimal, Field(ge=0, decimal_places=2, allow_inf_nan=False)]
Price = Annotated[Decimal, Field(gt=0, decimal_places=2, allow_inf_nan=False)]
Name = Annotated[str, Field(min_length=1, max_length=120)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_default=True)


class HealthResponse(ContractModel):
    status: Literal["ok"] = "ok"
    service: Literal["what-not-api"] = "what-not-api"


class NotImplementedResponse(ContractModel):
    detail: str
