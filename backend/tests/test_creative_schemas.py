import pytest
from pydantic import ValidationError


def test_creative_contract_exists():
    import importlib.util
    assert importlib.util.find_spec('app.schemas.creative'), 'Creative contracts must exist'


@pytest.mark.parametrize('category',['Video Editing','Travel Video Editing','Influencer Reel Editing','VFX'])
def test_approved_beta_creative_categories(category):
    from app.schemas.creative import ListingInput
    assert ListingInput(title='Edit',description='Creative work',category=category,pricing='QUOTATION',remote=True).category==category


@pytest.mark.parametrize('changes', [dict(pricing='QUOTATION', amount='10'), dict(amount=None), dict(remote=False), dict(category='Plumbing'), dict(portfolio=['javascript:alert(1)']), dict(currency='USD'), dict(title=' ')])
def test_listing_rejects_invalid_contract(changes):
    from app.schemas.creative import ListingInput
    with pytest.raises(ValidationError):
        ListingInput.model_validate(dict(title='Design', description='Brand design', category='Video Editing', pricing='FIXED', amount='100', remote=True, **{}) | changes)


def test_listing_supports_explicit_local_and_remote_scope():
    from app.schemas.creative import ListingInput
    assert ListingInput(title='Design', description='Brand', category='Video Editing', pricing='QUOTATION', remote=True).amount is None
    assert ListingInput(title='Photos', description='Portraits', category='Travel Video Editing', pricing='HOURLY', amount='500', remote=False, locality='Mumbai').locality == 'Mumbai'


def test_creative_view_preserves_decimal_transport():
    from decimal import Decimal
    from app.api.routes.creative import view
    from app.models.creative import CreativeResponse
    assert view(CreativeResponse(terms='Scope',amount=Decimal('120.10'),currency='INR',rfq_id=1))['amount']=='120.10'


def test_approval_requires_reviewed_timestamp_and_retry_keys_are_explicit():
    from app.schemas.creative import ModerationInput, RFQInput, ResponseInput
    for model,values in [(ModerationInput,dict(status='APPROVED')),(RFQInput,dict(brief='Brand')),(ResponseInput,dict(terms='Logo',amount='10'))]:
        with pytest.raises(ValidationError):model.model_validate(values)
