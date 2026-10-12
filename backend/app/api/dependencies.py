"""One session per request; write transaction scopes remain explicit."""
from collections.abc import Iterator

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import build_engine
from app.core.security import decode_access_token, InvalidCredentials
from app.models import User
from app.repositories.users import UserRepository
from app.services.errors import SellerNotFound
from app.services.sellers import SellerService


def get_session(request: Request) -> Iterator[Session]:
    application = request.app
    with application.state.database_engine_lock:
        if application.state.database_engine is None:
            if application.state.settings.database_url is None:
                raise HTTPException(503, 'Storage operation is unavailable')
            application.state.database_engine = build_engine(application.state.settings)
        engine = application.state.database_engine
    with Session(engine, expire_on_commit=False) as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                session.rollback()


def get_transaction_session(session: Session = Depends(get_session)) -> Iterator[Session]:
    """Begin before authentication's reads; finish before response delivery."""
    with session.begin():
        yield session


TransactionSession = Annotated[Session, Depends(get_transaction_session, scope='function')]
bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized():
    return HTTPException(401, 'Invalid authentication credentials', headers={'WWW-Authenticate': 'Bearer'})


def get_access_subject(request: Request,
                       credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> int:
    if credentials is None:
        raise unauthorized()
    token = credentials.credentials
    if len(token) > 4096 or token.count('.') != 2:
        raise unauthorized()
    try:
        return decode_access_token(token, request.app.state.settings)
    except InvalidCredentials:
        raise unauthorized() from None


def get_current_user(subject: int = Depends(get_access_subject),
                     session: Session = Depends(get_transaction_session, scope='function')) -> User:
    user = UserRepository(session).get(subject)
    if user is None or not user.is_active:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    def authorized(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(403, 'Operation is not permitted for this role')
        return user
    return authorized


require_active_user = get_current_user
require_buyer = require_role('BUYER')
require_seller = require_role('SELLER')
require_admin = require_role('ADMIN')
Buyer = Annotated[User, Depends(require_buyer)]
Seller = Annotated[User, Depends(require_seller)]
Admin = Annotated[User, Depends(require_admin)]
OrderActor = Annotated[User, Depends(require_role('BUYER', 'SELLER'))]


def current_seller_profile(session: Session, user_id: int):
    profile = SellerService(session).get_by_user(user_id)
    if profile is None:
        raise SellerNotFound('Create a complete seller profile first')
    return profile
