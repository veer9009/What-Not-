from types import SimpleNamespace
from decimal import Decimal

from app.schemas.location import Coordinate
from app.services.discovery import DiscoveryService


def product(latitude, longitude):
    return SimpleNamespace(id=1, seller_id=2, name='Vase', description='Clay', price='10.00',
        stock_quantity=2, category='Crafts', delivery_radius_km=1, images=[],
        seller=SimpleNamespace(latitude=Decimal(str(latitude)), longitude=Decimal(str(longitude)),
                               shop_name='Maker', is_verified=False))


def test_discovery_does_not_return_numeric_point_distance_or_private_coordinates():
    view = DiscoveryService(None)._eligible_view(product(0.004321, 0.005678),
        Coordinate(latitude=0, longitude=0)).model_dump()
    assert not {'distance_km', 'latitude', 'longitude', 'phone'} & view.keys()
    assert view['delivery_eligibility'] == 'CONFIRMED_AT_CHECKOUT'


def test_discovery_membership_is_identical_for_points_in_same_private_locality_cell():
    # Many arbitrary origin probes must observe the locality cell, not the private point.
    service = DiscoveryService(None)
    for longitude in ('-0.015', '-0.005', '0', '0.005', '0.015', '0.025'):
        source = Coordinate(latitude=0, longitude=longitude)
        first = service._eligible_view(product('0.001', '0.001'), source)
        second = service._eligible_view(product('0.009', '0.009'), source)
        assert (first is None) == (second is None)
        if first is not None:
            assert first.model_dump() == second.model_dump()
