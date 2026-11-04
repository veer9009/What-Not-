from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select, func
from app.models.events import AuditEvent, Notification, EmailOutbox
from app.services.orders import OrderService
from app.services.errors import InvalidOrderTransition, OwnershipError


def test_delivery_buyer_dispute_and_admin_resolution(db, records):
    order = records['order']
    order.status = 'OUT_FOR_DELIVERY'
    service = OrderService(db)
    service.transition(records['seller_user'].id, order.id, 'DELIVERED')
    assert order.delivered_at is not None
    assert order.confirmation_deadline > order.delivered_at
    service.transition(records['buyer'].id, order.id, 'DELIVERY_DISPUTED')
    assert service.auto_complete_due() == 0
    with pytest.raises(InvalidOrderTransition):
        service.transition(records['buyer'].id, order.id, 'COMPLETED')
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == 2


def test_auto_completion_is_bounded_and_once(db, records):
    order = records['order']
    order.status = 'DELIVERED'
    order.confirmation_deadline = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.flush()
    service = OrderService(db)
    assert service.auto_complete_due(limit=1) == 1
    assert service.auto_complete_due(limit=1) == 0
    assert order.status == 'COMPLETED'
    assert order.completion_source == 'TIMEOUT'
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == 1
    assert db.scalar(select(func.count()).select_from(Notification)) == 2


def test_fulfillment_access_window_omits_coordinates(db, records):
    service = OrderService(db)
    with pytest.raises(OwnershipError):
        service.fulfillment(records['seller_user'].id, records['order'].id)
    records['order'].status = 'ACCEPTED'
    view = service.fulfillment(records['seller_user'].id, records['order'].id)
    assert view['address_line1'] == '1 Maker Lane'
    assert 'latitude' not in view and 'longitude' not in view
    records['order'].status = 'COMPLETED'
    with pytest.raises(OwnershipError):
        service.fulfillment(records['seller_user'].id, records['order'].id)


def test_notification_deduplication_and_recipient_isolation(db, records):
    from app.services.notifications import publish_event, NotificationService
    args = (db, records['buyer'].id, 'test:event', 'TEST', 'order', records['order'].id, 'Update', 'Safe update')
    publish_event(*args)
    publish_event(*args)
    service = NotificationService(db)
    assert service.unread_count(records['buyer'].id) == 1
    assert service.unread_count(records['seller_user'].id) == 0
    row = service.list(records['buyer'].id)[0]
    with pytest.raises(OwnershipError):
        service.read_one(records['seller_user'].id, row.id)
    service.read_one(records['buyer'].id, row.id)
    assert service.unread_count(records['buyer'].id) == 0
    assert db.scalar(select(func.count()).select_from(EmailOutbox)) == 1


def test_admin_resolution_stock_disposition_and_repeat_guard(db, records):
    from app.models import User
    admin = User(name='Admin', email='resolution@example.test', phone='resolution', password_hash='hash', role='ADMIN')
    db.add(admin)
    db.flush()
    service = OrderService(db)
    order = records['order']
    original = records['product'].stock_quantity
    records['seller_user'].is_active = False
    db.flush()
    service.admin_resolve(admin.id, order.id, 'CANCEL_STRANDED', 'Suspended seller cannot fulfill')
    assert order.status == 'CANCELLED'
    assert records['product'].stock_quantity == original + records['item'].quantity
    with pytest.raises(InvalidOrderTransition):
        service.admin_resolve(admin.id, order.id, 'CANCEL_STRANDED', 'Repeated action')
    assert records['product'].stock_quantity == original + records['item'].quantity


def test_investigated_dispute_completion_does_not_restock(db, records):
    from app.models import User
    admin = User(name='Admin', email='dispute-resolution@example.test', phone='dispute-resolution', password_hash='hash', role='ADMIN')
    db.add(admin)
    db.flush()
    order = records['order']
    order.status = 'DELIVERY_DISPUTED'
    original = records['product'].stock_quantity
    OrderService(db).admin_resolve(admin.id, order.id, 'COMPLETE_DISPUTE', 'Delivery evidence investigated')
    assert order.status == 'COMPLETED' and order.completion_source == 'ADMIN'
    assert records['product'].stock_quantity == original


def test_expected_price_replay_returns_snapshot_before_current_price(db, records):
    from uuid import uuid4
    from app.services.inputs import OrderPlacement
    from app.services.errors import ProductUnavailable
    records['seller'].dispatch_location_confirmed_at = datetime.now(timezone.utc)
    records['product'].status = 'APPROVED'
    data = OrderPlacement(buyer_id=records['buyer'].id, seller_id=records['seller'].id,
        address_id=records['address'].id, idempotency_key=uuid4(),
        items=[dict(product_id=records['product'].id, quantity=1, expected_unit_price='250.00')])
    service = OrderService(db)
    order = service.create(data)
    records['product'].price = 300
    records['product'].is_active = False
    db.flush()
    assert service.create(data).id == order.id
    assert order.items[0].unit_price == 250
    changed = data.model_copy(update={'idempotency_key': uuid4()})
    with pytest.raises(ProductUnavailable):
        service.create(changed)
