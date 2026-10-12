from pydantic import EmailStr, TypeAdapter
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.users import UserRepository
from app.services.errors import InactiveUser, InvalidRole, UserNotFound
from app.services.inputs import Phone, StrictBool, UserCreate
from app.services.operations import write_operation


def pagination(offset, limit):
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Use offset >= 0 and limit between 1 and 100')
    return offset, limit


def require_user(session, user_id, *, role=None, active=True, lock=False):
    user = UserRepository(session).get(user_id, lock=lock)
    if user is None:
        raise UserNotFound('User does not exist')
    if active and not user.is_active:
        raise InactiveUser('User is inactive')
    if role is not None and user.role != role:
        raise InvalidRole(f'Operation requires role {role}')
    return user


class UserService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = UserRepository(session)

    @write_operation
    def create(self, data: UserCreate):
        data = UserCreate.model_validate(data)
        values = data.model_dump()
        values['role'] = data.role.value
        values['password_hash'] = data.password_hash.get_secret_value()
        return self.repository.add(User(**values))

    def get(self, user_id: int):
        return require_user(self.session, user_id, active=False)

    def get_by_email(self, email: str):
        return self.repository.by_email(str(TypeAdapter(EmailStr).validate_python(email)))

    def get_by_phone(self, phone: str):
        return self.repository.by_phone(TypeAdapter(Phone).validate_python(phone))

    def list(self, *, offset=0, limit=100):
        return self.repository.list(*pagination(offset, limit))

    @write_operation
    def set_active(self, user_id: int, is_active: bool):
        value = TypeAdapter(StrictBool).validate_python(is_active)
        user = require_user(self.session, user_id, active=False, lock=True)
        user.is_active = value
        return user
