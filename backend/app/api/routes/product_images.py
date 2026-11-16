from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from fastapi.security import APIKeyQuery
from starlette.concurrency import run_in_threadpool

from app.api.contracts import IdentifierPath
from app.api.dependencies import Seller, TransactionSession
from app.schemas.common import ContractModel
from app.schemas.product import ProductResponse, ProductImageResponse
from app.services.abuse import check_action_limit
from app.services.mappers import product_response
from app.services.product_images import ProductImageService, owned_product, verify_image_token
from app.storage.product_images import MAX_IMAGE_BYTES, ImageValidationError, ImageStorageError

router = APIRouter(tags=['Product images'])
capability_scheme = APIKeyQuery(name='token', auto_error=False)


async def image_bytes(request):
    length = request.headers.get('content-length')
    if length is not None:
        try:
            if int(length) < 0:
                raise ValueError()
            if int(length) > MAX_IMAGE_BYTES:
                raise HTTPException(413, 'Images must be 5 MB or smaller')
        except ValueError:
            raise HTTPException(400, 'Invalid upload size') from None
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_IMAGE_BYTES:
            raise HTTPException(413, 'Images must be 5 MB or smaller')
        data.extend(chunk)
    return bytes(data)


async def upload(request, user, session, product_id, image_id=None):
    # Authorization precedes body consumption, decoding and storage writes.
    await run_in_threadpool(owned_product, session, user.id, product_id)
    settings = request.app.state.settings
    await run_in_threadpool(check_action_limit, session, settings, 'image_upload', user.id)
    raw = await image_bytes(request)
    try:
        product = await run_in_threadpool(ProductImageService(session, settings).upload,
                                         user.id, product_id, raw, image_id)
        return product_response(product, settings)
    except ImageValidationError:
        raise HTTPException(422, 'Choose a valid static JPG, PNG or WebP image, up to 5 MB and 16 million pixels') from None
    except ImageStorageError:
        raise HTTPException(503, 'Image storage is unavailable; please retry later') from None


@router.get('/products/{product_id}/images', response_model=list[ProductImageResponse])
def list_images(product_id: IdentifierPath, user: Seller, session: TransactionSession, request: Request):
    product = owned_product(session, user.id, product_id)
    return product_response(product, request.app.state.settings).images


@router.post('/products/{product_id}/images', response_model=ProductResponse, status_code=201,
             description='Upload raw JPG/PNG/WebP bytes, maximum 5 MiB; seller ownership required.')
async def add_image(product_id: IdentifierPath, user: Seller, session: TransactionSession, request: Request):
    return await upload(request, user, session, product_id)


@router.post('/products/{product_id}/images/{image_id}/replace', response_model=ProductResponse)
async def replace_image(product_id: IdentifierPath, image_id: IdentifierPath,
                        user: Seller, session: TransactionSession, request: Request):
    return await upload(request, user, session, product_id, image_id)


@router.post('/products/{product_id}/images/{image_id}/remove', response_model=ProductResponse)
def remove_image(product_id: IdentifierPath, image_id: IdentifierPath, payload: ContractModel,
                 user: Seller, session: TransactionSession, request: Request):
    product = ProductImageService(session, request.app.state.settings).remove(user.id, product_id, image_id)
    return product_response(product, request.app.state.settings)


@router.post('/products/{product_id}/images/{image_id}/primary', response_model=ProductResponse)
def set_primary(product_id: IdentifierPath, image_id: IdentifierPath, payload: ContractModel,
                user: Seller, session: TransactionSession, request: Request):
    product = ProductImageService(session, request.app.state.settings).primary(user.id, product_id, image_id)
    return product_response(product, request.app.state.settings)


def validated_key(key: str, request: Request, token: str | None = Security(capability_scheme)):
    return verify_image_token(key, token, request.app.state.settings)


@router.get('/product-images/{key}', response_class=Response,
            description='Private image delivery using a short-lived image capability, not an access token.')
def image_content(key: str, request: Request, verified: Annotated[str, Depends(validated_key)],
                  session: TransactionSession):
    try:
        raw = ProductImageService(session, request.app.state.settings).read(verified)
    except ImageStorageError:
        raise HTTPException(503, 'Image storage is unavailable; please retry later') from None
    return Response(raw, media_type='image/webp', headers={'Cache-Control': 'private, no-store',
                    'Content-Disposition': 'inline; filename="product.webp"',
                    'X-Content-Type-Options': 'nosniff'})
