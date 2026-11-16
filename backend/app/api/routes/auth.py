from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.api.dependencies import CurrentUser, TransactionSession
from app.core.security import create_access_token, signing_key
from app.schemas.auth import LoginRequest, TokenResponse, UserRegistration
from app.schemas.user import PublicUserResponse
from app.services.auth import AuthService
from app.services.mappers import user_response
from app.services.abuse import require_beta_admission, check_action_limit
from app.services.refresh_sessions import RefreshSessionService

REFRESH_COOKIE = 'wn_refresh'
COOKIE_PATH = '/api/v1/auth'


def require_auth_csrf(request: Request):
    origin = request.headers.get('origin')
    allowed = request.app.state.settings.cors_origins
    same_origin = str(request.base_url).rstrip('/')
    if (request.headers.get('x-whatnot-csrf') != '1' or not origin
            or origin not in [*allowed, same_origin]
            or request.headers.get('sec-fetch-site', '').lower() == 'cross-site'):
        raise HTTPException(403, 'Untrusted authentication request')


def set_refresh_cookie(response, raw, expires_at, max_age=None):
    # TIMESTAMPTZ values may arrive in the connection's local timezone. Cookie
    # dates require UTC; reject ambiguous naive values rather than guessing.
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise ValueError('Refresh cookie expiry must be timezone-aware')
    expires_at = expires_at.astimezone(timezone.utc)
    if max_age is None:
        max_age = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
    response.set_cookie(REFRESH_COOKIE, raw, max_age=max_age, expires=expires_at,
                        httponly=True, secure=True, samesite='strict', path=COOKIE_PATH)


def clear_refresh_cookie(response):
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH, httponly=True,
                           secure=True, samesite='strict')


def token_response(user, family, settings):
    return TokenResponse(access_token=create_access_token(user.id, settings, session_id=family.id),
                         expires_in=900, user=user_response(user))


def admit_auth(request, session, email):
    settings=request.app.state.settings
    require_beta_admission(settings,email)
    source=request.client.host if request.client else 'unknown'
    check_action_limit(session,settings,'auth',f'source:{source}')
    check_action_limit(session,settings,'auth',f'email:{email}')

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post('/register', response_model=PublicUserResponse, status_code=201,
             description='Create a BUYER or SELLER user. No seller profile is created; ADMIN is forbidden.')
def register(payload: UserRegistration, request: Request, response: Response, session: TransactionSession):
    signing_key(request.app.state.settings)
    admit_auth(request,session,str(payload.email))
    response.headers['Cache-Control'] = 'no-store'
    return user_response(AuthService(session).register(payload))


@router.post('/login', response_model=TokenResponse, dependencies=[Depends(require_auth_csrf)],
             description='Verify credentials and return a short-lived Bearer access token.')
def login(payload: LoginRequest, request: Request, response: Response, session: TransactionSession):
    settings = request.app.state.settings
    signing_key(settings)
    admit_auth(request,session,str(payload.email))
    user = AuthService(session).login(payload)
    family, raw = RefreshSessionService(session).create(user, request.cookies.get(REFRESH_COOKIE))
    set_refresh_cookie(response, raw, family.expires_at)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    return token_response(user, family, settings)


@router.post('/refresh', response_model=TokenResponse, dependencies=[Depends(require_auth_csrf)])
def refresh(request: Request, response: Response, session: TransactionSession):
    settings = request.app.state.settings
    signing_key(settings)
    source = request.client.host if request.client else 'unknown'
    check_action_limit(session, settings, 'auth', f'source:{source}')
    result = RefreshSessionService(session).rotate(request.cookies.get(REFRESH_COOKIE))
    if result is None:
        # Returning, rather than raising, preserves replay/suspension revocation.
        denied = JSONResponse({'detail': 'Invalid authentication credentials'}, status_code=401,
            headers={'Cache-Control': 'no-store', 'WWW-Authenticate': 'Bearer'})
        clear_refresh_cookie(denied)
        return denied
    user, family, raw = result
    require_beta_admission(settings, user.email)
    set_refresh_cookie(response, raw, family.expires_at)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    return token_response(user, family, settings)


@router.post('/logout', status_code=204, dependencies=[Depends(require_auth_csrf)])
def logout(request: Request, session: TransactionSession):
    RefreshSessionService(session).revoke(request.cookies.get(REFRESH_COOKIE))
    response = Response(status_code=204, headers={'Cache-Control': 'no-store'})
    clear_refresh_cookie(response)
    return response


@router.get('/me', response_model=PublicUserResponse, description='Return the active authenticated database user.')
def me(user: CurrentUser, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return user_response(user)
