from fastapi import APIRouter, Response

from app.api.contracts import IdentifierPath
from app.api.dependencies import Buyer, TransactionSession
from app.schemas.discovery import BuyerProduct, DiscoveryQuery, DiscoverySource
from app.services.discovery import DiscoveryService

router = APIRouter(prefix='/discovery', tags=['Discovery'])


@router.post('/products', response_model=list[BuyerProduct],
             description='Read geographically eligible products using an explicit owned address or transient location.')
def list_products(payload: DiscoveryQuery, user: Buyer, session: TransactionSession, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return DiscoveryService(session).list(user.id, payload)


@router.post('/products/{product_id}', response_model=BuyerProduct,
             description='Read an eligible product; absence and ineligibility both return 404.')
def get_product(product_id: IdentifierPath, payload: DiscoverySource, user: Buyer,
                session: TransactionSession, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return DiscoveryService(session).get(user.id, product_id, payload)
