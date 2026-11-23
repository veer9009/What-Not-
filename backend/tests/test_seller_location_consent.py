"""Dispatch moves must require fresh public discovery consent; no database access."""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.schemas.location import Coordinate
from app.schemas.public_discovery import PublicDiscoveryConfirmation
from app.services import sellers
from app.services.discovery import DiscoveryService
from app.services.inputs import SellerUpdate


@pytest.fixture
def seller_service(monkeypatch):
    seller = SimpleNamespace(
        id=7, user_id=11, shop_name='Synthetic shop', is_verified=False,
        latitude=Decimal('12.000000'), longitude=Decimal('77.000000'),
        dispatch_location_confirmed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        public_discovery_latitude=Decimal('12.001000'),
        public_discovery_longitude=Decimal('77.001000'),
        public_discovery_confirmed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        public_discovery_consent_version='public-discovery-v1',
    )
    # Only persistence and user lookup are replaced; mutation/validation and
    # discovery eligibility run their production implementations.
    repository = SimpleNamespace(get=lambda seller_id, **kwargs: seller,
                                 by_user=lambda user_id: seller)
    monkeypatch.setattr(sellers, 'SellerRepository', lambda session: repository)
    monkeypatch.setattr(sellers, 'require_user', lambda *args, **kwargs: None)
    return sellers.SellerService(None), seller


def public_state(seller):
    return (seller.public_discovery_latitude, seller.public_discovery_longitude,
            seller.public_discovery_confirmed_at, seller.public_discovery_consent_version)


def mutate_dispatch(service, path, coordinates):
    if path == 'update':
        return service.update.__wrapped__(service, 11, 7, SellerUpdate(**coordinates))
    return service.set_dispatch_location.__wrapped__(service, 11, Coordinate(**coordinates))


@pytest.mark.parametrize('path', ['update', 'set_dispatch_location'])
@pytest.mark.parametrize('changed', [
    {'latitude': '12.002000', 'longitude': '77.000000'},
    {'latitude': '12.000000', 'longitude': '77.002000'},
    {'latitude': '12.002000', 'longitude': '77.002000'},
])
def test_dispatch_move_revokes_public_point_and_hides_products(seller_service, path, changed):
    service, seller = seller_service
    product = SimpleNamespace(
        seller=seller, id=21, seller_id=7, name='Synthetic product', description='Example',
        price=Decimal('1.00'), stock_quantity=1, category='Crafts',
        delivery_radius_km=3, images=[],
    )
    location = Coordinate(latitude=12, longitude=77)
    discovery = DiscoveryService(None)
    assert discovery._eligible_view(product, location, 3) is not None

    result = mutate_dispatch(service, path, changed)

    assert result is seller
    assert seller.latitude == Decimal(changed['latitude'])
    assert seller.longitude == Decimal(changed['longitude'])
    assert public_state(seller) == (None, None, None, None)
    assert discovery._eligible_view(product, location, 3) is None
    if path == 'update':
        assert seller.dispatch_location_confirmed_at is None
    else:
        assert seller.dispatch_location_confirmed_at is not None


@pytest.mark.parametrize('path', ['update', 'set_dispatch_location'])
def test_same_numeric_dispatch_point_preserves_separate_public_point_and_consent(seller_service, path):
    service, seller = seller_service
    original_public_state = public_state(seller)
    original_confirmation = seller.dispatch_location_confirmed_at

    mutate_dispatch(service, path, {'latitude': '12.0', 'longitude': '77'})

    assert public_state(seller) == original_public_state
    assert seller.dispatch_location_confirmed_at is not None
    if path == 'update':
        assert seller.dispatch_location_confirmed_at == original_confirmation


def test_non_location_profile_update_preserves_consent(seller_service):
    service, seller = seller_service
    original_public_state = public_state(seller)
    original_confirmation = seller.dispatch_location_confirmed_at

    service.update.__wrapped__(service, 11, 7, SellerUpdate(shop_name='Renamed synthetic shop'))

    assert seller.shop_name == 'Renamed synthetic shop'
    assert public_state(seller) == original_public_state
    assert seller.dispatch_location_confirmed_at == original_confirmation


def test_partial_coordinate_update_revokes_consent(seller_service):
    service, seller = seller_service

    service.update.__wrapped__(service, 11, 7, SellerUpdate(latitude='12.002'))

    assert seller.longitude == Decimal('77.000000')
    assert public_state(seller) == (None, None, None, None)


def test_fresh_explicit_public_confirmation_keeps_public_and_private_points_separate(seller_service):
    service, seller = seller_service
    mutate_dispatch(service, 'set_dispatch_location', {'latitude': '12.002', 'longitude': '77.002'})

    service.set_public_discovery.__wrapped__(service, 11, PublicDiscoveryConfirmation(
        latitude='12.003', longitude='77.003', consent=True, consent_version='public-discovery-v1'))

    assert (seller.latitude, seller.longitude) == (Decimal('12.002'), Decimal('77.002'))
    assert public_state(seller)[:2] == (Decimal('12.003'), Decimal('77.003'))
    assert seller.public_discovery_confirmed_at is not None
    assert seller.public_discovery_consent_version == 'public-discovery-v1'
