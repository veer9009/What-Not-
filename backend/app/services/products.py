from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.models import Product, ProductImage
from app.repositories.products import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.errors import InvalidProductTransition, ProductNotFound
from app.services.inputs import StrictBool
from app.services.operations import write_operation
from app.services.sellers import owned_seller
from app.services.users import pagination, require_user
from app.services.validation import revalidate_patch


def require_product(session, product_id, *, lock=False):
    product = ProductRepository(session).get(product_id, lock=lock)
    if product is None:
        raise ProductNotFound('Product does not exist')
    return product


def set_primary_image(product, image_url):
    primary = next((image for image in product.images if image.is_primary), None)
    if image_url is None:
        if primary is not None:
            product.images.remove(primary)
    elif primary is not None:
        primary.image_url = str(image_url)
    else:
        product.images.append(ProductImage(image_url=str(image_url), is_primary=True, sort_order=0))


class ProductService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = ProductRepository(session)

    @write_operation
    def create(self, actor_id: int, seller_id: int, data: ProductCreate):
        data = ProductCreate.model_validate(data)
        require_user(self.session, actor_id, lock=True)
        owned_seller(self.session, actor_id, seller_id)
        values = data.model_dump(exclude={'image_url'})
        values['category'] = data.category.value
        product = Product(seller_id=seller_id, status='PENDING', rejection_reason=None, is_active=True, **values)
        set_primary_image(product, data.image_url)
        return self.repository.add(product)

    def get(self, product_id: int):
        """Internal read, not a buyer-visible or geographically eligible detail."""
        return require_product(self.session, product_id)

    def list_for_seller(self, actor_id: int, seller_id: int, *, offset=0, limit=100):
        owned_seller(self.session, actor_id, seller_id)
        return self.repository.for_seller(seller_id, *pagination(offset, limit))

    def list_buyer_candidates_without_geography(self, *, offset=0, limit=100):
        """APPROVED + active + stock only; future callers MUST apply geographic eligibility."""
        return self.repository.buyer_candidates_without_geography(*pagination(offset, limit))

    def _owned_locked(self, actor_id, product_id):
        require_user(self.session, actor_id, lock=True)
        product = require_product(self.session, product_id, lock=True)
        owned_seller(self.session, actor_id, product.seller_id)
        return product

    @write_operation
    def update(self, actor_id: int, product_id: int, data: ProductUpdate):
        data = revalidate_patch(ProductUpdate, data)
        product = self._owned_locked(actor_id, product_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            if key == 'image_url':
                set_primary_image(product, value)
            else:
                setattr(product, key, value.value if key == 'category' else value)
        if product.status == 'APPROVED':
            product.status, product.rejection_reason = 'PENDING', None
        return product

    @write_operation
    def set_active(self, actor_id: int, product_id: int, is_active: bool):
        value = TypeAdapter(StrictBool).validate_python(is_active)
        product = self._owned_locked(actor_id, product_id)
        product.is_active = value
        return product

    @write_operation
    def resubmit(self, actor_id: int, product_id: int):
        product = self._owned_locked(actor_id, product_id)
        if product.status != 'REJECTED':
            raise InvalidProductTransition('Only rejected products can be resubmitted')
        product.status, product.rejection_reason = 'PENDING', None
        return product
