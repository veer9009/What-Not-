from sqlalchemy.orm import Session

from app.models import Address
from app.repositories.addresses import AddressRepository
from app.services.errors import AddressInUse, AddressNotFound, AddressOwnershipError
from app.services.inputs import AddressCreate, AddressUpdate
from app.services.operations import write_operation
from app.services.users import require_user
from app.services.validation import revalidate_patch


def owned_address(session, user_id, address_id, *, lock=False):
    address = AddressRepository(session).get(address_id, lock=lock)
    if address is None:
        raise AddressNotFound('Address does not exist')
    if address.user_id != user_id:
        raise AddressOwnershipError('Address belongs to another user')
    return address


class AddressService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = AddressRepository(session)

    @write_operation
    def create(self, user_id: int, data: AddressCreate):
        data = AddressCreate.model_validate(data)
        require_user(self.session, user_id, lock=True)
        if data.is_default:
            self.repository.clear_default(user_id)
        return self.repository.add(Address(user_id=user_id, **data.model_dump()))

    def get(self, user_id: int, address_id: int):
        require_user(self.session, user_id)
        return owned_address(self.session, user_id, address_id)

    def list(self, user_id: int):
        require_user(self.session, user_id)
        return self.repository.for_user(user_id)

    @write_operation
    def update(self, user_id: int, address_id: int, data: AddressUpdate):
        data = revalidate_patch(AddressUpdate, data)
        require_user(self.session, user_id, lock=True)
        address = owned_address(self.session, user_id, address_id, lock=True)
        values = data.model_dump(exclude_unset=True)
        delivery_changes = {key: value for key, value in values.items()
                            if key not in {'label', 'is_default'} and getattr(address, key) != value}
        if delivery_changes and self.repository.referenced(address_id):
            raise AddressInUse('Create a replacement address; delivery fields are part of order history')
        if values.get('is_default'):
            self.repository.clear_default(user_id)
        for key, value in values.items():
            setattr(address, key, value)
        return address

    def set_default(self, user_id: int, address_id: int):
        return self.update(user_id, address_id, AddressUpdate(is_default=True))
