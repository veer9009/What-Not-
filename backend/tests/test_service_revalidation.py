from decimal import Decimal

import pytest
from pydantic import SecretStr, ValidationError

from app.schemas.product import ProductCreate
from app.services.inputs import OrderPlacement, UserCreate


def test_mutated_product_input_is_revalidated():
    data = ProductCreate(name='Vase', description='Handmade', price='1.00', stock_quantity=1, category='Crafts', delivery_radius_km=1)
    data.price = Decimal('0')
    with pytest.raises(ValidationError):
        ProductCreate.model_validate(data)


def test_mutated_user_hash_is_revalidated():
    data = UserCreate(name='Buyer', email='buyer@example.com', phone='123', password_hash='$2b$12$' + 'a' * 53, role='BUYER')
    data.password_hash = SecretStr('plaintext')
    with pytest.raises(ValidationError):
        UserCreate.model_validate(data)


def test_mutated_nested_order_item_is_revalidated():
    data = OrderPlacement(buyer_id=1, seller_id=1, address_id=1, items=[dict(product_id=1, quantity=1)])
    data.items[0].quantity = True
    with pytest.raises(ValidationError):
        OrderPlacement.model_validate(data)


def test_emptied_order_items_are_revalidated():
    data = OrderPlacement(buyer_id=1, seller_id=1, address_id=1, items=[dict(product_id=1, quantity=1)])
    data.items.clear()
    with pytest.raises(ValidationError):
        OrderPlacement.model_validate(data)


def test_implicit_transaction_is_rejected_before_flush():
    from sqlalchemy.orm import Session
    from app.models import User
    from app.services.users import UserService
    with Session() as session:
        session.add(User(name='Unrelated pending row'))
        data = UserCreate(name='Buyer', email='buyer@example.com', phone='123', password_hash='$2b$12$' + 'a' * 53, role='BUYER')
        with pytest.raises(RuntimeError, match='explicit outer transaction'):
            UserService(session).create(data)


@pytest.mark.parametrize('identifier', [True, '1', 0, -1, 2**63, None])
def test_service_ids_are_validated_before_database_access(identifier):
    from sqlalchemy.orm import Session
    from app.services.users import UserService
    with Session() as session:
        with pytest.raises(ValidationError):
            UserService(session).get(identifier)


def test_mutated_patch_is_rejected_by_validation_not_serialization_warning():
    from sqlalchemy.orm import Session
    from app.schemas.product import ProductUpdate
    from app.services.products import ProductService
    data = ProductUpdate(stock_quantity=1)
    data.stock_quantity = 'invalid'
    with Session() as session, session.begin():
        with pytest.raises(ValidationError):
            ProductService(session).update(1, 1, data)
