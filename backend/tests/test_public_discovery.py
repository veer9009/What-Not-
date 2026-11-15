import math
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from app.schemas.discovery import DiscoveryQuery, DiscoverySource
from app.schemas.public_discovery import PublicDiscoveryConfirmation
from app.services.discovery import DiscoveryService


@pytest.mark.parametrize('radius',[1,2,3])
def test_strict_radius_and_defaults(radius):
    assert DiscoveryQuery(address_id=1,radius_km=radius).radius_km==radius
    assert DiscoverySource(address_id=1).radius_km==3


@pytest.mark.parametrize('radius',[True,False,'1',1.5,0,4,None])
def test_invalid_radius(radius):
    with pytest.raises(ValidationError):DiscoveryQuery(address_id=1,radius_km=radius)


@pytest.mark.parametrize('consent',[False,1,'true',None])
def test_explicit_public_consent(consent):
    with pytest.raises(ValidationError):
        PublicDiscoveryConfirmation(latitude=0,longitude=0,consent=consent,consent_version='public-discovery-v1')


def test_consent_version():
    with pytest.raises(ValidationError):
        PublicDiscoveryConfirmation(latitude=0,longitude=0,consent=True,consent_version='old')


@pytest.mark.parametrize('radius',[1,2,3])
def test_public_radius_inclusive_and_outside(radius):
    from app.services.geography import EARTH_RADIUS_KM
    seller=SimpleNamespace(latitude=0,longitude=0,public_discovery_latitude=0,
        public_discovery_longitude=0,public_discovery_confirmed_at=object(),
        public_discovery_consent_version='public-discovery-v1',shop_name='Synthetic',is_verified=False)
    product=SimpleNamespace(seller=seller,id=1,seller_id=1,name='Synthetic',description='Synthetic',price=1,
        stock_quantity=1,category='Crafts',delivery_radius_km=3,images=[])
    service=DiscoveryService(None)
    # Unrounded geometry boundary test; database precision gets separate tests.
    location=SimpleNamespace(latitude=0,longitude=math.degrees(radius/EARTH_RADIUS_KM))
    assert service._eligible_view(product,location,radius) is not None
    location.longitude+=.000001
    assert service._eligible_view(product,location,radius) is None
    product.delivery_radius_km=1
    assert service._eligible_view(product,SimpleNamespace(latitude=0,longitude=.02),3) is None


def test_unset_public_point_excluded():
    seller=SimpleNamespace(public_discovery_latitude=None,public_discovery_longitude=None,
        public_discovery_confirmed_at=None,public_discovery_consent_version=None)
    assert DiscoveryService(None)._eligible_view(SimpleNamespace(seller=seller),SimpleNamespace(latitude=0,longitude=0),3) is None


def test_readiness_accepts_new_schema():
    from app.api.routes.health import readiness
    values=iter(['0009',0,0,None])
    assert readiness(SimpleNamespace(scalar=lambda statement:next(values)))['schema']=='0009'


def test_readiness_rejects_old_schema():
    from app.api.routes.health import readiness
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        readiness(SimpleNamespace(scalar=lambda statement:'0008'))
    assert error.value.status_code==503


@pytest.mark.parametrize('latitude,longitude,buyer_latitude,buyer_longitude',[
    (0,179.999,0,-179.999),(89.999,0,89.999,180),(-89.999,0,-89.999,180)])
def test_public_distance_at_dateline_and_poles(latitude,longitude,buyer_latitude,buyer_longitude):
    seller=SimpleNamespace(latitude=latitude,longitude=longitude,public_discovery_latitude=latitude,
        public_discovery_longitude=longitude,public_discovery_confirmed_at=object(),
        public_discovery_consent_version='public-discovery-v1',shop_name='Synthetic',is_verified=False)
    product=SimpleNamespace(seller=seller,id=1,seller_id=1,name='Synthetic',description='Synthetic',price=1,
        stock_quantity=1,category='Crafts',delivery_radius_km=1,images=[])
    assert DiscoveryService(None)._eligible_view(product,SimpleNamespace(latitude=buyer_latitude,longitude=buyer_longitude),1) is not None


def test_radius_filter_precedes_pagination_across_repository_batches():
    from copy import copy
    seller=SimpleNamespace(latitude=0,longitude=0,public_discovery_latitude=0,public_discovery_longitude=0,
        public_discovery_confirmed_at=object(),public_discovery_consent_version='public-discovery-v1',shop_name='Synthetic',is_verified=False)
    product=SimpleNamespace(seller=seller,id=101,seller_id=1,name='Synthetic',description='Synthetic',price=1,
        stock_quantity=1,category='Crafts',delivery_radius_km=3,images=[])
    far_seller=copy(seller);far_seller.public_discovery_latitude=1
    far=[]
    for i in range(1,101):
        p=copy(product);p.id=i;p.seller=far_seller;far.append(p)
    close=[]
    for i in range(101,104):
        p=copy(product);p.id=i;close.append(p)
    service=DiscoveryService(None)
    service.repository=SimpleNamespace(discovery_candidates=lambda after,limit:far if after==0 else close if after==100 else [])
    service._location=lambda actor,query:query.location
    result=service.list(1,DiscoveryQuery(location={'latitude':0,'longitude':0},radius_km=1,offset=1,limit=1))
    assert [p.id for p in result]==[102]
