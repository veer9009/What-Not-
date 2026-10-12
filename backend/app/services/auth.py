"""Public registration/login; only this boundary accepts plaintext passwords."""
from app.core.security import (InvalidCredentials, dummy_password_hash, hash_password,
                               password_hasher, verify_password)
from app.repositories.users import UserRepository
from app.schemas.auth import LoginRequest, UserRegistration
from app.services.errors import DuplicateUser
from app.services.inputs import UserCreate
from app.services.operations import write_operation
from app.services.users import UserService


class AuthService:
    def __init__(self, session):
        self.session = session
        self.repository = UserRepository(session)

    @write_operation
    def register(self, data: UserRegistration):
        data = UserRegistration.model_validate(data)
        if self.repository.by_normalized_email(data.email) or self.repository.by_phone(data.phone):
            raise DuplicateUser('Email or phone already exists')
        return UserService(self.session).create(UserCreate(name=data.name, email=data.email,
            phone=data.phone, role=data.role, password_hash=hash_password(data.password.get_secret_value())))

    @write_operation
    def login(self, data: LoginRequest):
        data = LoginRequest.model_validate(data)
        matches = self.repository.by_normalized_email(data.email)
        user = matches[0] if len(matches) == 1 else None
        encoded = user.password_hash if user is not None and user.is_active else dummy_password_hash()
        valid = verify_password(data.password.get_secret_value(), encoded)
        if user is None or not user.is_active or not valid:
            raise InvalidCredentials()
        user = self.repository.get(user.id, lock=True)
        if not user.is_active or not verify_password(data.password.get_secret_value(), user.password_hash):
            raise InvalidCredentials()
        if not user.password_hash.startswith('$argon2id$') or password_hasher.check_needs_rehash(user.password_hash):
            user.password_hash = hash_password(data.password.get_secret_value())
        return user
