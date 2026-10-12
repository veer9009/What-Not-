from fastapi import APIRouter, Request, Response

from app.api.dependencies import CurrentUser, TransactionSession
from app.core.security import create_access_token, signing_key
from app.schemas.auth import LoginRequest, TokenResponse, UserRegistration
from app.schemas.user import PublicUserResponse
from app.services.auth import AuthService
from app.services.mappers import user_response

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post('/register', response_model=PublicUserResponse, status_code=201,
             description='Create a BUYER or SELLER user. No seller profile is created; ADMIN is forbidden.')
def register(payload: UserRegistration, request: Request, response: Response, session: TransactionSession):
    signing_key(request.app.state.settings)
    response.headers['Cache-Control'] = 'no-store'
    return user_response(AuthService(session).register(payload))


@router.post('/login', response_model=TokenResponse,
             description='Verify credentials and return a short-lived Bearer access token.')
def login(payload: LoginRequest, request: Request, response: Response, session: TransactionSession):
    settings = request.app.state.settings
    signing_key(settings)
    user = AuthService(session).login(payload)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    return TokenResponse(access_token=create_access_token(user.id, settings),
                         expires_in=settings.access_token_expire_minutes * 60, user=user_response(user))


@router.get('/me', response_model=PublicUserResponse, description='Return the active authenticated database user.')
def me(user: CurrentUser, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return user_response(user)
