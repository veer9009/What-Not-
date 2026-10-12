from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.validation import database_id


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: int, *, lock=False):
        query = select(User).where(User.id == database_id(user_id))
        if lock:
            query = query.with_for_update(read=lock == 'shared').execution_options(populate_existing=True)
        return self.session.scalar(query)

    def by_email(self, email: str):
        return self.session.scalar(select(User).where(User.email == email))

    def by_phone(self, phone: str):
        return self.session.scalar(select(User).where(User.phone == phone))

    def list(self, offset: int, limit: int):
        return list(self.session.scalars(select(User).order_by(User.id).offset(offset).limit(limit)))

    def add(self, user: User):
        self.session.add(user)
        return user
