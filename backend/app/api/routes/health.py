from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Process health only; this does not report database readiness."""
    return HealthResponse()
