from fastapi import APIRouter

from app.api.contracts import PLACEHOLDER_DESCRIPTION, PLACEHOLDER_RESPONSES, not_implemented
from app.schemas.auth import LoginRequest, UserRegistration
from app.schemas.common import NotImplementedResponse
from app.schemas.user import PublicUserResponse

router = APIRouter(prefix="/auth", tags=["Auth"], responses=PLACEHOLDER_RESPONSES)


@router.post("/register", response_model=PublicUserResponse, status_code=201, description=PLACEHOLDER_DESCRIPTION)
async def register(payload: UserRegistration) -> PublicUserResponse:
    not_implemented()


@router.post("/login", response_model=NotImplementedResponse, status_code=501, description=PLACEHOLDER_DESCRIPTION)
async def login(payload: LoginRequest) -> NotImplementedResponse:
    not_implemented()
