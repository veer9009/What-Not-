"""Owned image mutations and expiring delivery capabilities; no public bucket."""
import hmac
import time

import jwt
from fastapi import HTTPException
from sqlalchemy import select

from app.core.security import signing_key
from app.models import ProductImage, Product, SellerProfile, User
from app.services.operations import write_operation
from app.services.products import ProductService
from app.services.sellers import owned_seller
from app.services.errors import ProductNotFound
from app.storage.product_images import (image_key, managed_reference, new_image_key,
                                       normalize_image, get_image_storage)


def delivery_key(settings):
    return hmac.digest(signing_key(settings).encode(), b'whatnot-product-image-v1', 'sha256')


def signed_image_url(reference, settings):
    key = image_key(reference)
    if key is None:
        return None
    token = jwt.encode({'purpose': 'product-image', 'key': key,
                        'exp': int(time.time()) + settings.image_url_ttl_seconds},
                       delivery_key(settings), algorithm='HS256')
    return f'{settings.image_delivery_origin}/api/v1/product-images/{key}?token={token}'


def verify_image_token(key, token, settings):
    try:
        if image_key(managed_reference(key)) != key or not token or len(token) > 2048:
            raise ValueError()
        claims = jwt.decode(token, delivery_key(settings), algorithms=['HS256'],
                            options={'require': ['exp', 'purpose', 'key']})
        if claims['purpose'] != 'product-image' or claims['key'] != key:
            raise ValueError()
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(404, 'Image is unavailable') from None
    return key


def owned_product(session, actor_id, product_id, *, lock=False):
    products = ProductService(session)
    if lock:
        return products._owned_locked(actor_id, product_id)
    product = products.get(product_id)
    owned_seller(session, actor_id, product.seller_id)
    return product


def reset_moderation(product):
    # A primary switch is also a visible edit; retain rejected reasons until resubmission.
    if product.status == 'APPROVED':
        product.status, product.rejection_reason = 'PENDING', None
    # Touch the product so moderation's optimistic timestamp covers image changes.
    from sqlalchemy import func
    product.updated_at = func.clock_timestamp()


class ProductImageService:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings

    @write_operation
    def upload(self, actor_id, product_id, raw, replace_id=None):
        product = owned_product(self.session, actor_id, product_id, lock=True)
        target = self.find(product, replace_id) if replace_id is not None else None
        if target is None and len(product.images) >= 5:
            raise HTTPException(409, 'A product can have at most five images')
        normalized = normalize_image(raw)
        storage = get_image_storage(self.settings)
        key = new_image_key()
        storage.put(key, normalized)
        # Immutable private blobs can outlive a rolled-back write. They cannot be
        # read without a live attachment; offline cleanup is documented separately.
        if target is None:
            target = ProductImage(image_url=managed_reference(key),
                is_primary=not any(i.is_primary for i in product.images),
                sort_order=max((i.sort_order for i in product.images), default=-1) + 1)
            product.images.append(target)
        else:
            target.image_url = managed_reference(key)
        reset_moderation(product)
        return product

    def find(self, product, image_id):
        image = next((i for i in product.images if i.id == image_id), None)
        if image is None:
            raise ProductNotFound('Product image does not exist')
        return image

    @write_operation
    def remove(self, actor_id, product_id, image_id):
        product = owned_product(self.session, actor_id, product_id, lock=True)
        target = self.find(product, image_id)
        primary = target.is_primary
        product.images.remove(target)
        self.session.flush()
        if primary and product.images:
            product.images[0].is_primary = True
        reset_moderation(product)
        return product

    @write_operation
    def primary(self, actor_id, product_id, image_id):
        product = owned_product(self.session, actor_id, product_id, lock=True)
        target = self.find(product, image_id)
        # Flush the old flag before setting another: the partial index is immediate.
        for image in product.images:
            image.is_primary = False
        self.session.flush()
        target.is_primary = True
        reset_moderation(product)
        return product

    def read(self, key):
        attached = self.session.scalar(select(ProductImage.id)
            .join(Product, Product.id == ProductImage.product_id)
            .join(SellerProfile, SellerProfile.id == Product.seller_id)
            .join(User, User.id == SellerProfile.user_id)
            .where(ProductImage.image_url == managed_reference(key),
                   Product.is_active.is_(True), User.is_active.is_(True), User.role == 'SELLER'))
        if attached is None:
            raise HTTPException(404, 'Image is unavailable')
        try:
            return get_image_storage(self.settings).get(key)
        except FileNotFoundError:
            raise HTTPException(404, 'Image is unavailable') from None
