from fastapi import APIRouter, Request

from app.api.dependencies import Seller, TransactionSession, current_seller_profile
from app.schemas.marketplace import SellerResponse, seller_response
from app.schemas.product import ProductResponse
from app.services.inputs import SellerCreate, SellerUpdate
from app.services.sellers import SellerService
from app.services.mappers import product_response
from app.schemas.location import Coordinate
from app.schemas.common import ContractModel
from app.schemas.public_discovery import PublicDiscoveryConfirmation

router = APIRouter(prefix='/sellers', tags=['Sellers'])


@router.patch('/me/public-discovery-location', response_model=SellerResponse,
              description='Confirm an explicitly consented public discovery point owned by the authenticated seller.')
def confirm_public_discovery(payload: PublicDiscoveryConfirmation, user: Seller, session: TransactionSession):
    return seller_response(SellerService(session).set_public_discovery(user.id, payload))


@router.post('/me/public-discovery-location/revoke', response_model=SellerResponse)
def revoke_public_discovery(payload: ContractModel, user: Seller, session: TransactionSession):
    return seller_response(SellerService(session).set_public_discovery(user.id, None))


@router.patch('/me/dispatch-location', response_model=SellerResponse,
              description='Explicitly confirm or update the authenticated seller business/dispatch location.')
def set_dispatch_location(payload: Coordinate, user: Seller, session: TransactionSession):
    return seller_response(SellerService(session).set_dispatch_location(user.id, payload))


@router.post('/me', response_model=SellerResponse, status_code=201, description='Create a complete profile for the authenticated SELLER.')
def create_profile(payload: SellerCreate, user: Seller, session: TransactionSession):
    return seller_response(SellerService(session).create(user.id, payload))


@router.get('/me', response_model=SellerResponse, description='Read the authenticated seller profile.')
def get_profile(user: Seller, session: TransactionSession):
    return seller_response(current_seller_profile(session, user.id))


@router.patch('/me', response_model=SellerResponse, description='Edit own shop fields. Owner and verification state cannot be changed.')
def update_profile(payload: SellerUpdate, user: Seller, session: TransactionSession):
    profile = current_seller_profile(session, user.id)
    return seller_response(SellerService(session).update(user.id, profile.id, payload))


@router.get('/me/products', response_model=list[ProductResponse], description='List owned seller products, without implying buyer delivery eligibility.')
def list_products(user: Seller, session: TransactionSession, request: Request):
    profile = current_seller_profile(session, user.id)
    return [product_response(product, request.app.state.settings) for product in SellerService(session).list_products(user.id, profile.id)]
