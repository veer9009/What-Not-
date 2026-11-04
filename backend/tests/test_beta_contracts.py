from app.schemas.order import OrderCreate, OrderStatus


def test_beta_lifecycle_and_expected_price_contract():
    assert 'COMPLETED' in OrderStatus.__members__
    assert 'DELIVERY_DISPUTED' in OrderStatus.__members__
    request = OrderCreate(seller_id=1, address_id=1, items=[dict(product_id=1, quantity=1, expected_unit_price='12.00')])
    assert str(request.items[0].expected_unit_price) == '12.00'


def test_shared_event_models_and_publisher_exist():
    from app.models.events import AuditEvent, Notification, EmailOutbox
    from app.services.notifications import publish_event
    assert callable(publish_event)
    assert Notification.__table__.c.recipient_id is not None
    assert EmailOutbox.__table__.c.lease_token is not None
    assert AuditEvent.__table__.c.previous_status is not None
