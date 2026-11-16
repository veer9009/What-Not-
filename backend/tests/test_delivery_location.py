from types import SimpleNamespace
import pytest
from app.services.orders import OrderService


@pytest.mark.parametrize('point', [(None, None), ('NaN', '0'), ('0', '181')])
def test_historical_unusable_delivery_point_preserves_postal_fallback(monkeypatch, point):
    buyer = SimpleNamespace(id=1, role='BUYER', name='Buyer', phone='100')
    address = SimpleNamespace(latitude=point[0], longitude=point[1], address_line1='Postal lane',
        address_line2=None, city='City', state='State', pincode='400001')
    order = SimpleNamespace(id=9, buyer_id=1, buyer=buyer, address=address)
    monkeypatch.setattr('app.services.orders.require_user', lambda *_: buyer)
    service = OrderService(None)
    service.repository = SimpleNamespace(get=lambda _: order)
    monkeypatch.setattr(service, '_delivery_location_confirmed', lambda _: False)
    response = service.fulfillment(1, 9)
    assert response['delivery_location'] is None
    assert response['address_line1'] == 'Postal lane'
