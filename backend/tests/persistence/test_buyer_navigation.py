import pytest
from app.models import User
from app.models.events import AuditEvent
from sqlalchemy import select
from test_authentication import auth_client
from test_authorization import bearer


def test_buyer_confirms_immutable_order_address_before_seller_navigation(auth_client, db, records, caplog):
    order = records['order']
    order.status = 'ACCEPTED'
    db.flush()
    path = f'/api/v1/orders/{order.id}'
    buyer, seller = bearer(records['buyer'].id), bearer(records['seller_user'].id)
    point = {'latitude': '19.070000', 'longitude': '72.870000'}
    assert auth_client.get(path+'/fulfillment', headers=seller).json()['delivery_location'] is None
    assert auth_client.get(path+'/fulfillment', headers=buyer).json()['delivery_location'] == point
    confirm = path+'/delivery-location-confirmation'
    assert auth_client.get(path+'/fulfillment').status_code == 401
    assert auth_client.post(confirm, json=point).status_code == 401
    assert auth_client.post(confirm, headers=seller, json=point).status_code == 403
    assert auth_client.post(confirm, headers=buyer, json={**point, 'latitude': '19.08'}).status_code == 409
    assert auth_client.post(confirm, headers=buyer, json=point).status_code == 200
    assert auth_client.post(confirm, headers=buyer, json=point).status_code == 200
    data = auth_client.get(path+'/fulfillment', headers=seller).json()
    assert data['delivery_location'] == point
    assert data['delivery_location_confirmed'] is True
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.action == 'DELIVERY_LOCATION_CONFIRMED')))
    assert len(events) == 1
    assert '19.07' not in events[0].reason and '72.87' not in events[0].reason
    assert '19.07' not in caplog.text and '72.87' not in caplog.text
    for suffix in ['', '/orders']:
        url = path if not suffix else '/api/v1/orders'
        text = auth_client.get(url, headers=seller).text
        assert 'latitude' not in text and 'longitude' not in text


@pytest.mark.parametrize('status', ['PLACED', 'COMPLETED', 'CANCELLED', 'REJECTED'])
def test_navigation_keeps_seller_fulfillment_status_boundary(auth_client, db, records, status):
    order = records['order']
    path = f'/api/v1/orders/{order.id}'
    buyer = bearer(records['buyer'].id)
    assert auth_client.post(path+'/delivery-location-confirmation', headers=buyer,
        json={'latitude': '19.070000', 'longitude': '72.870000'}).status_code == 200
    order.status = status
    db.flush()
    assert auth_client.get(path+'/fulfillment', headers=bearer(records['seller_user'].id)).status_code == 403


@pytest.mark.parametrize('role', ['BUYER', 'SELLER'])
def test_unrelated_users_cannot_read_or_confirm_location(auth_client, db, records, role):
    other = User(name='Other', email='navigation-other@example.test', phone='other-nav', password_hash='test', role=role)
    db.add(other)
    records['order'].status = 'ACCEPTED'
    db.flush()
    path = f"/api/v1/orders/{records['order'].id}"
    headers = bearer(other.id)
    assert auth_client.get(path+'/fulfillment', headers=headers).status_code == 403
    assert auth_client.post(path+'/delivery-location-confirmation', headers=headers,
        json={'latitude': '19.070000', 'longitude': '72.870000'}).status_code == 403


@pytest.mark.parametrize('point', [{'latitude': 'NaN', 'longitude': '0'}, {'latitude': '91', 'longitude': '0'},
    {'latitude': '0', 'longitude': '-181'}, {'latitude': '0'}, {'latitude': None, 'longitude': None}])
def test_confirmation_validates_coordinates(auth_client, records, point):
    path = f"/api/v1/orders/{records['order'].id}/delivery-location-confirmation"
    assert auth_client.post(path, headers=bearer(records['buyer'].id), json=point).status_code == 422
