"""Sanitized HTTP boundary: never send SQL, exception inputs or secrets."""
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import AuthenticationUnavailable, InvalidCredentials
from app.services import errors
from app.services.abuse import RateLimitExceeded
import logging

logger = logging.getLogger('whatnot.api')


def install_error_handlers(app):
    @app.exception_handler(RateLimitExceeded)
    async def rate_error(request, exc):
        return JSONResponse(status_code=429, content={'detail':'Request limit reached; retry later'},
                            headers={'Retry-After':str(exc.retry_after),'Cache-Control':'no-store'})
    @app.exception_handler(InvalidCredentials)
    async def credentials_error(request, exc):
        return JSONResponse(status_code=401, content={'detail': 'Invalid authentication credentials'},
                            headers={'WWW-Authenticate': 'Bearer', 'Cache-Control': 'no-store'})

    @app.exception_handler(AuthenticationUnavailable)
    async def configuration_error(request, exc):
        return JSONResponse(status_code=503, content={'detail': 'Authentication is unavailable'})

    @app.exception_handler(errors.ServiceError)
    async def domain_error(request, exc):
        logger.warning('domain_request_rejected', extra={'error_code':type(exc).__name__})
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
        content = {'detail': str(exc)}
        if isinstance(exc, errors.DeliveryIneligible):
            content['code'] = 'DELIVERY_INELIGIBLE'
        if isinstance(exc, errors.IdempotencyConflict):
            content['code'] = 'IDEMPOTENCY_CONFLICT'
        return JSONResponse(status_code=status, content=content)

    @app.exception_handler(SQLAlchemyError)
    async def storage_error(request, exc):
        logger.error('storage_operation_failed', extra={'error_code':type(exc).__name__})
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
        logger.error('response_validation_failed', extra={'error_code':type(exc).__name__})
        return JSONResponse(status_code=500, content={'detail': 'Response could not be produced'})
