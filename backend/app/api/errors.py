"""Sanitized HTTP boundary: never send SQL, exception inputs or secrets."""
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import AuthenticationUnavailable, InvalidCredentials
from app.services import errors


def install_error_handlers(app):
    @app.exception_handler(InvalidCredentials)
    async def credentials_error(request, exc):
        return JSONResponse(status_code=401, content={'detail': 'Invalid authentication credentials'},
                            headers={'WWW-Authenticate': 'Bearer', 'Cache-Control': 'no-store'})

    @app.exception_handler(AuthenticationUnavailable)
    async def configuration_error(request, exc):
        return JSONResponse(status_code=503, content={'detail': 'Authentication is unavailable'})

    @app.exception_handler(errors.ServiceError)
    async def domain_error(request, exc):
        if isinstance(exc, errors.InactiveUser):
            return JSONResponse(status_code=401, content={'detail': 'Invalid authentication credentials'},
                                headers={'WWW-Authenticate': 'Bearer'})
        if isinstance(exc, (errors.InvalidRole, errors.OwnershipError)):
            status = 403
        elif isinstance(exc, (errors.UserNotFound, errors.SellerNotFound, errors.ProductNotFound,
                              errors.AddressNotFound, errors.OrderNotFound)):
            status = 404
        else:
            status = 409
        return JSONResponse(status_code=status, content={'detail': str(exc)})

    @app.exception_handler(SQLAlchemyError)
    async def storage_error(request, exc):
        return JSONResponse(status_code=503, content={'detail': 'Storage operation is unavailable'})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Omit input and ctx: both can contain submitted passwords/unknown fields.
        return JSONResponse(status_code=422, content={'detail': [
            {'loc': ['body'] if error['type'] == 'extra_forbidden' else list(error['loc']),
             'type': error['type'], 'msg': 'Invalid request value'}
            for error in exc.errors()]})

    @app.exception_handler(ResponseValidationError)
    @app.exception_handler(ValidationError)
    async def response_error(request, exc):
        return JSONResponse(status_code=500, content={'detail': 'Response could not be produced'})
