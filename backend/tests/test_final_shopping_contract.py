from app.schemas.checkout import CheckoutInput
from app.services.payment_settings import PaymentSettingsService
from app.services.checkout import CheckoutService
from app.services.wishlist import WishlistService

def test_checkout_rejects_empty_seller_groups():
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        CheckoutInput.model_validate({'address_id':1,'sellers':[]})

def test_upi_is_disabled_without_policy():
    from app.core.config import Settings
    assert not Settings(_env_file=None).prepaid_upi_enabled
