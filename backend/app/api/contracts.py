from typing import Annotated, NoReturn

from fastapi import HTTPException, Path

from app.schemas.common import MAX_BIGINT, NotImplementedResponse

IdentifierPath = Annotated[int, Path(gt=0, le=MAX_BIGINT, description="Positive PostgreSQL BIGINT identifier")]
PLACEHOLDER_DESCRIPTION = (
    "Not implemented: buyer geographic eligibility is unavailable. This contract returns "
    "HTTP 501 for valid requests; no discovery or checkout is performed. Invalid requests return HTTP 422."
)
PLACEHOLDER_RESPONSES = {
    501: {"model": NotImplementedResponse, "description": "Not implemented; no data is stored or retrieved."}
}


def not_implemented() -> NoReturn:
    raise HTTPException(status_code=501, detail="Not implemented: buyer geographic eligibility is unavailable.")
