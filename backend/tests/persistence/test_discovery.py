from datetime import datetime, timezone

import pytest

from app.models import Product
from test_authentication import auth_client
from test_authorization import bearer

PATH = '/api/v1/discovery/products'
SOURCE = {'location': {'latitude': 19.076, 'longitude': 72.8777}}


@pytest.fixture
def available(records, db):
    records['seller'].dispatch_location_confirmed_at = datetime.now(timezone.utc)
    records['product'].status = 'APPROVED'
    db.flush()
    return records


def test_transient_and_owned_address_discovery_safe_responses(auth_client, available):
    r = available
    headers = bearer(r['buyer'].id)
    for source in [SOURCE, {'address_id': r['address'].id}]:
        response = auth_client.post(PATH, json=source, headers=headers)
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        product = response.json()[0]
        assert product['id'] == r['product'].id
        assert product['seller_id'] == r['seller'].id
        assert product['shop_name'] == 'Local maker'
        assert isinstance(product['distance_km'], (float, int))
        assert not {'latitude', 'longitude', 'phone', 'user_id', 'dispatch_location_confirmed_at', 'address_id', 'seller'} & product.keys()
        detail = auth_client.post(f"{PATH}/{r['product'].id}", json=source, headers=headers)
        assert detail.status_code == 200
        assert detail.json() == product
        assert detail.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('target,field,value', [
    ('product', 'status', 'PENDING'), ('product', 'status', 'REJECTED'),
    ('product', 'is_active', False), ('product', 'stock_quantity', 0),
    ('seller', 'dispatch_location_confirmed_at', None),
    ('seller_user', 'is_active', False), ('seller_user', 'role', 'BUYER'),
    ('seller', 'latitude', 20),
])
def test_all_availability_predicates_and_hidden_detail(auth_client, available, db, target, field, value):
    setattr(available[target], field, value)
    db.flush()
    headers = bearer(available['buyer'].id)
    assert auth_client.post(PATH, json=SOURCE, headers=headers).json() == []
    assert auth_client.post(f"{PATH}/{available['product'].id}", json=SOURCE, headers=headers).status_code == 404


@pytest.mark.parametrize('radius', [1, 2, 3])
def test_each_radius_and_unrounded_outside_point(auth_client, available, db, radius):
    p = available['product']
    p.delivery_radius_km = radius
    available['seller'].latitude = 0
    available['seller'].longitude = 0
    db.flush()
    headers = bearer(available['buyer'].id)
    # One degree along the equator is ~111.195 km. Literal coordinates straddle each boundary.
    inside, outside = {1: (.008993, .008994), 2: (.017986, .017987), 3: (.026979, .026980)}[radius]
    def query(longitude):
        return auth_client.post(PATH, json={'location': {'latitude': 0, 'longitude': longitude}}, headers=headers)
    assert len(query(inside).json()) == 1
    assert query(outside).json() == []


def test_dispatch_move_changes_next_discovery_request(auth_client, available):
    buyer = bearer(available['buyer'].id)
    seller = bearer(available['seller_user'].id)
    assert len(auth_client.post(PATH, json=SOURCE, headers=buyer).json()) == 1
    assert auth_client.patch('/api/v1/sellers/me/dispatch-location', json={'latitude': 0, 'longitude': 0}, headers=seller).status_code == 200
    assert auth_client.post(PATH, json=SOURCE, headers=buyer).json() == []


def test_pagination_after_more_than_100_ineligible_candidates(auth_client, available, db):
    p = available['product']
    p.delivery_radius_km = 1
    available['seller'].latitude = 0
    available['seller'].longitude = 0
    for n in range(104):
        db.add(Product(seller_id=p.seller_id, name=f'Far {n}', description='Far', price=1,
            stock_quantity=1, category='Crafts', delivery_radius_km=1, status='APPROVED'))
    eligible = []
    for n in range(3):
        product = Product(seller_id=p.seller_id, name=f'Near {n}', description='Near', price=1,
            stock_quantity=1, category='Crafts', delivery_radius_km=3, status='APPROVED')
        db.add(product)
        eligible.append(product)
    db.flush()
    source = {'location': {'latitude': 0, 'longitude': .02}, 'offset': 1, 'limit': 1}
    result = auth_client.post(PATH, json=source, headers=bearer(available['buyer'].id))
    assert result.status_code == 200
    assert [p['id'] for p in result.json()] == [eligible[1].id]


@pytest.mark.parametrize('actor,status', [(None, 401), ('seller_user', 403), ('buyer', 200)])
def test_discovery_roles(auth_client, available, actor, status):
    headers = bearer(available[actor].id) if actor else {}
    assert auth_client.post(PATH, json=SOURCE, headers=headers).status_code == status


def test_inactive_buyer_admin_and_other_address_are_rejected(auth_client, available, db):
    r = available
    r['buyer'].is_active = False
    db.flush()
    assert auth_client.post(PATH, json=SOURCE, headers=bearer(r['buyer'].id)).status_code == 401
    r['buyer'].is_active = True
    r['buyer'].role = 'ADMIN'
    db.flush()
    assert auth_client.post(PATH, json=SOURCE, headers=bearer(r['buyer'].id)).status_code == 403
    r['buyer'].role = 'BUYER'
    r['seller_user'].role = 'BUYER'
    db.flush()
    foreign = auth_client.post(PATH, json={'address_id': r['address'].id}, headers=bearer(r['seller_user'].id))
    assert foreign.status_code == 403
    missing = auth_client.post(PATH, json={'address_id': 9223372036854775807}, headers=bearer(r['buyer'].id))
    assert missing.status_code == 404


def test_invalid_requests_do_not_echo_coordinates(auth_client, available):
    headers = bearer(available['buyer'].id)
    for body in [{}, {**SOURCE, 'buyer_id': 1}, {'location': {'latitude': 91.123456, 'longitude': 0}},
                 {**SOURCE, 'address_id': available['address'].id}, {**SOURCE, 'distance_km': 0}]:
        response = auth_client.post(PATH, json=body, headers=headers)
        assert response.status_code == 422
        assert '91.123456' not in response.text
    assert auth_client.post(f'{PATH}/9223372036854775807', json=SOURCE, headers=headers).status_code == 404
