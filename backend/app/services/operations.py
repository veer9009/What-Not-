"""Savepoint protection within the caller's explicit outer transaction."""
from functools import wraps

from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import SessionTransactionOrigin

from app.services.errors import DuplicateSeller, DuplicateUser, PersistenceConflict


def write_operation(method):
    @wraps(method)
    def protected(self, *args, **kwargs):
        transaction = self.session.get_transaction()
        if transaction is None or transaction.origin is not SessionTransactionOrigin.BEGIN:
            raise RuntimeError('Write services require an explicit outer transaction')
        try:
            with self.session.begin_nested():
                result = method(self, *args, **kwargs)
                self.session.flush()
                return result
        except IntegrityError as exc:
            name = getattr(getattr(exc.orig, 'diag', None), 'constraint_name', None)
            if name in {'uq_users_email', 'uq_users_phone'}:
                raise DuplicateUser('Email or phone already exists') from None
            if name == 'uq_seller_profiles_user_id':
                raise DuplicateSeller('User already has a seller profile') from None
            raise PersistenceConflict('Operation conflicts with stored data') from None
        except DataError:
            raise PersistenceConflict('Value cannot be stored') from None
    return protected
