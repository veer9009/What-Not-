from fastapi import APIRouter

from app.api.contracts import IdentifierPath
from app.api.dependencies import CurrentUser, TransactionSession
from app.schemas.marketplace import AddressResponse, address_response
from app.services.addresses import AddressService
from app.services.inputs import AddressCreate, AddressUpdate

router = APIRouter(prefix='/addresses', tags=['Addresses'])


@router.get('', response_model=list[AddressResponse], description='List only the authenticated user addresses.')
def list_addresses(user: CurrentUser, session: TransactionSession):
    return [address_response(address) for address in AddressService(session).list(user.id)]


@router.post('', response_model=AddressResponse, status_code=201, description='Create an address owned by the authenticated user.')
def create_address(payload: AddressCreate, user: CurrentUser, session: TransactionSession):
    return address_response(AddressService(session).create(user.id, payload))


@router.get('/{address_id}', response_model=AddressResponse, description='Read only an owned address.')
def get_address(address_id: IdentifierPath, user: CurrentUser, session: TransactionSession):
    return address_response(AddressService(session).get(user.id, address_id))


@router.patch('/{address_id}', response_model=AddressResponse, description='Edit only an owned address; preserve delivery fields referenced by orders.')
def update_address(address_id: IdentifierPath, payload: AddressUpdate, user: CurrentUser, session: TransactionSession):
    return address_response(AddressService(session).update(user.id, address_id, payload))


@router.post('/{address_id}/default', response_model=AddressResponse, description='Make an owned address the default atomically.')
def set_default(address_id: IdentifierPath, user: CurrentUser, session: TransactionSession):
    return address_response(AddressService(session).set_default(user.id, address_id))
