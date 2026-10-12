"""Library cryptography only; no role or personal data in access tokens."""
from datetime import datetime, timezone
from functools import lru_cache
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.profiles import RFC_9106_LOW_MEMORY
import bcrypt
import jwt

from app.core.config import Settings
from app.schemas.common import MAX_BIGINT

password_hasher = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)


class InvalidCredentials(Exception):
    """Same externally visible failure for all invalid account credentials."""


class AuthenticationUnavailable(Exception):
    """Fail closed when the signing key is not configured."""


def signing_key(settings: Settings) -> str:
    if settings.jwt_secret_key is None:
        raise AuthenticationUnavailable()
    return settings.jwt_secret_key.get_secret_value()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        if encoded.startswith(('$2a$', '$2b$', '$2y$')):
            raw = password.encode('utf-8')
            return len(raw) <= 72 and bcrypt.checkpw(raw, encoded.encode('ascii'))
        return password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError, ValueError, UnicodeError):
        return False


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    return hash_password(secrets.token_urlsafe(32))


def create_access_token(user_id: int, settings: Settings) -> str:
    now = int(datetime.now(timezone.utc).timestamp())
    return jwt.encode({'sub': str(user_id), 'iat': now,
                       'exp': now + settings.access_token_expire_minutes * 60},
                      signing_key(settings), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> int:
    key = signing_key(settings)
    try:
        claims = jwt.decode(token, key, algorithms=[settings.jwt_algorithm],
                            options={'require': ['sub', 'iat', 'exp']})
        subject = claims['sub']
        if not isinstance(subject, str) or not re.fullmatch(r'[1-9][0-9]{0,18}', subject):
            raise InvalidCredentials()
        user_id = int(subject)
        if user_id > MAX_BIGINT:
            raise InvalidCredentials()
        if type(claims['iat']) is not int or type(claims['exp']) is not int or claims['exp'] <= claims['iat']:
            raise InvalidCredentials()
        return user_id
    except jwt.InvalidTokenError:
        raise InvalidCredentials() from None
