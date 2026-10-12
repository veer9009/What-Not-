from sqlalchemy.orm import Session

from app.models import SellerProfile
from app.repositories.sellers import SellerRepository
from app.repositories.products import ProductRepository
from app.services.errors import DuplicateSeller, OwnershipError, SellerNotFound
from app.services.inputs import SellerCreate, SellerUpdate
from app.services.operations import write_operation
from app.services.users import pagination, require_user
from app.services.validation import revalidate_patch


def require_seller(session, seller_id):
    seller = SellerRepository(session).get(seller_id)
    if seller is None:
        raise SellerNotFound('Seller profile does not exist')
    return seller


def owned_seller(session, actor_id, seller_id):
    seller = require_seller(session, seller_id)
    if seller.user_id != actor_id:
        raise OwnershipError('Seller profile belongs to another user')
    require_user(session, actor_id, role='SELLER')
    return seller


class SellerService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = SellerRepository(session)

    @write_operation
    def create(self, user_id: int, data: SellerCreate):
        data = SellerCreate.model_validate(data)
        require_user(self.session, user_id, role='SELLER', lock=True)
        if self.repository.by_user(user_id) is not None:
            raise DuplicateSeller('User already has a seller profile')
        return self.repository.add(SellerProfile(user_id=user_id, **data.model_dump()))

    def get(self, seller_id: int):
        return require_seller(self.session, seller_id)

    def get_by_user(self, user_id: int):
        require_user(self.session, user_id, active=False)
        return self.repository.by_user(user_id)

    @write_operation
    def update(self, actor_id: int, seller_id: int, data: SellerUpdate):
        data = revalidate_patch(SellerUpdate, data)
        require_user(self.session, actor_id, lock=True)
        owned_seller(self.session, actor_id, seller_id)
        seller = self.repository.get(seller_id, lock=True)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(seller, key, value)
        return seller

    def list_products(self, actor_id: int, seller_id: int, *, offset=0, limit=100):
        owned_seller(self.session, actor_id, seller_id)
        return ProductRepository(self.session).for_seller(seller_id, *pagination(offset, limit))
