"""Order navigation policy on synthetic objects; no records or schema are changed."""
from types import SimpleNamespace
from decimal import Decimal
import pytest
from app.services import orders as module
from app.services.errors import OwnershipError


def service(monkeypatch, status, confirmed, actor_id=2):
    # Replace only reads, leaving fulfillment's real ownership/status/consent logic intact.
    actor = SimpleNamespace(id=actor_id, role='SELLER')
    monkeypatch.setattr(module, 'require_user', lambda session, user_id: actor)
    monkeypatch.setattr(module, 'require_seller', lambda session, seller_id: SimpleNamespace(user_id=2))
    point = SimpleNamespace(latitude=0, longitude=0, address_line1='Synthetic street',
        address_line2=None, city='Synthetic city', state='Synthetic state', pincode='000000')
    order = SimpleNamespace(id=9, buyer_id=1, seller_id=8, status=status, address=point,
        buyer=SimpleNamespace(name='Synthetic buyer', phone='synthetic'))
    instance = module.OrderService(SimpleNamespace(scalar=lambda query:1 if confirmed else None))
    instance.repository = SimpleNamespace(get=lambda order_id:order)
    return instance


@pytest.mark.parametrize('status',['ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','DELIVERY_DISPUTED'])
@pytest.mark.parametrize('confirmed',[True,False])
def test_only_confirmed_point_reaches_assigned_seller_in_eligible_status(monkeypatch,status,confirmed):
    data = service(monkeypatch,status,confirmed).fulfillment(2,9)
    assert data['delivery_location_confirmed'] is confirmed
    assert (data['delivery_location'] is not None) is confirmed
    if confirmed:
        # This service boundary returns Decimals; the HTTP schema serializes them.
        assert data['delivery_location']=={'latitude':Decimal('0'),'longitude':Decimal('0')}


@pytest.mark.parametrize('status',['PLACED','CANCELLED','COMPLETED','REJECTED'])
@pytest.mark.parametrize('confirmed',[True,False])
def test_ineligible_order_status_never_exposes_seller_fulfillment(monkeypatch,status,confirmed):
    with pytest.raises(OwnershipError):
        service(monkeypatch,status,confirmed).fulfillment(2,9)


@pytest.mark.parametrize('status',['ACCEPTED','OUT_FOR_DELIVERY','DELIVERED'])
def test_unrelated_seller_cannot_read_even_confirmed_destination(monkeypatch,status):
    with pytest.raises(OwnershipError):
        service(monkeypatch,status,True,actor_id=3).fulfillment(3,9)
