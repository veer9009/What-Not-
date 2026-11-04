from test_authentication import auth_client
from test_authorization import bearer
from app.services.notifications import publish_event


def test_notification_http_recipient_boundary_and_read_all(auth_client, db, records):
    publish_event(db, records['buyer'].id, 'http:1', 'TEST', 'order', records['order'].id, 'Order update', 'Status changed')
    buyer = bearer(records['buyer'].id)
    seller = bearer(records['seller_user'].id)
    assert auth_client.get('/api/v1/notifications').status_code == 401
    response = auth_client.get('/api/v1/notifications', headers=buyer)
    assert response.status_code == 200
    row = response.json()[0]
    assert 'recipient_id' not in row and 'event_key' not in row
    assert auth_client.get('/api/v1/notifications', headers=seller).json() == []
    assert auth_client.patch(f"/api/v1/notifications/{row['id']}/read", headers=seller).status_code == 403
    assert auth_client.get('/api/v1/notifications/unread-count', headers=buyer).json() == {'count': 1}
    assert auth_client.patch('/api/v1/notifications/read-all', headers=buyer).json() == {'updated': 1}
    assert auth_client.get('/api/v1/notifications/unread-count', headers=buyer).json() == {'count': 0}
    assert auth_client.patch('/api/v1/notifications/read-all', headers=buyer).json() == {'updated': 0}


def test_fulfillment_http_ownership_state_and_no_coordinates(auth_client, db, records):
    order = records['order']
    route = f'/api/v1/orders/{order.id}/fulfillment'
    seller = bearer(records['seller_user'].id)
    buyer = bearer(records['buyer'].id)
    assert auth_client.get(route, headers=seller).status_code == 403
    assert auth_client.get(route, headers=buyer).status_code == 200
    order.status = 'ACCEPTED'
    db.flush()
    result = auth_client.get(route, headers=seller)
    assert result.status_code == 200
    assert set(result.json()) == {'recipient_name', 'phone', 'address_line1', 'address_line2', 'city', 'state', 'pincode'}
    order.status = 'COMPLETED'
    db.flush()
    assert auth_client.get(route, headers=seller).status_code == 403


def test_public_new_order_requires_price_but_historical_replay_survives(auth_client, db, records):
    from datetime import datetime, timezone
    from uuid import uuid4
    from app.services.inputs import OrderPlacement
    from app.services.orders import OrderService
    records['seller'].dispatch_location_confirmed_at = datetime.now(timezone.utc)
    records['product'].status = 'APPROVED'
    db.flush()
    payload = dict(seller_id=records['seller'].id, address_id=records['address'].id,
        items=[dict(product_id=records['product'].id, quantity=1)])
    headers = {**bearer(records['buyer'].id), 'Idempotency-Key': str(uuid4())}
    response = auth_client.post('/api/v1/orders', json=payload, headers=headers)
    assert response.status_code == 409
    assert records['product'].stock_quantity == 5
    historical_key = uuid4()
    historical = OrderService(db).create(OrderPlacement(buyer_id=records['buyer'].id,
        idempotency_key=historical_key, **payload))
    records['product'].price = 999
    records['product'].is_active = False
    db.flush()
    replay = auth_client.post('/api/v1/orders', json=payload,
        headers={**bearer(records['buyer'].id), 'Idempotency-Key': str(historical_key)})
    assert replay.status_code == 201
    assert replay.json()['id'] == historical.id
