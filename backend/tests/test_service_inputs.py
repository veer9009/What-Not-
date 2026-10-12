from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.product import ProductCreate
from app.schemas.order import OrderItem


@pytest.mark.parametrize('field,value', [('price', '10000000000.00'), ('stock_quantity', 2147483648)])
def test_product_input_fits_database(field, value):
    data = dict(name='Vase', description='Handmade', price='1.00', stock_quantity=1,
                category='Crafts', delivery_radius_km=1)
    with pytest.raises(ValidationError):
        ProductCreate(**{**data, field: value})


def test_order_quantity_fits_database():
    with pytest.raises(ValidationError):
        OrderItem(product_id=1, quantity=2147483648)


@pytest.mark.parametrize('value', ['plaintext-password', '', '  ', '$2b$fake', '$argon2id$fake'])
def test_internal_user_rejects_unrecognized_password_hash(value):
    from app.services.inputs import UserCreate
    with pytest.raises(ValidationError):
        UserCreate(name='Buyer', email='buyer@example.com', phone='123',
                   password_hash=value, role='BUYER')


def test_fee_policy_is_exact_configurable_and_nonnegative():
    from app.services.orders import DeliveryFeePolicy
    assert DeliveryFeePolicy().calculate() == Decimal('0.00')
    assert DeliveryFeePolicy('49.00').calculate() == Decimal('49.00')
    for value in ['-1', 'NaN', 'Infinity', '0.001', '10000000000.00']:
        with pytest.raises(ValidationError):
            DeliveryFeePolicy(value)
