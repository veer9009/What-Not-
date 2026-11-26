from datetime import datetime, timezone
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from app.models import Order, User, SellerProfile, Product
from app.models.payment import OrderPayment
from app.models.events import Notification
from app.models.shopping import SellerPaymentSettings, WishlistItem
from app.services.checkout import CheckoutService
from app.services.payment_settings import PaymentSettingsService
from app.services.wishlist import WishlistService
from app.services.payments import PaymentService
from app.services.errors import PersistenceConflict, ProductUnavailable, IdempotencyConflict, OwnershipError
from app.core.config import Settings
from test_authentication import auth_client
from test_authorization import bearer

def ready(db,records):
    from app.schemas.public_discovery import PUBLIC_DISCOVERY_CONSENT_VERSION
    records['seller'].dispatch_location_confirmed_at=datetime.now(timezone.utc)
    records['seller'].public_discovery_latitude=records['seller'].latitude
    records['seller'].public_discovery_longitude=records['seller'].longitude
    records['seller'].public_discovery_confirmed_at=datetime.now(timezone.utc)
    records['seller'].public_discovery_consent_version=PUBLIC_DISCOVERY_CONSENT_VERSION
    records['product'].status='APPROVED'
    db.flush()
    return dict(address_id=records['address'].id,sellers=[dict(seller_id=records['seller'].id,payment_method='COD',items=[dict(product_id=records['product'].id,quantity=1,expected_unit_price='250.00')])])

def test_preview_never_writes_and_missing_method_fails(db,records):
    payload=ready(db,records);payload['sellers'][0].pop('payment_method')
    before=db.scalar(select(func.count()).select_from(Order))
    preview=CheckoutService(db).preview(records['buyer'].id,payload)
    assert preview['total']=='250.00' and preview['groups'][0]['available_payment_methods']==['COD']
    assert db.scalar(select(func.count()).select_from(Order))==before
    assert db.scalar(select(func.count()).select_from(Notification))==0
    assert records['product'].stock_quantity==5
    with pytest.raises(PersistenceConflict):CheckoutService(db).create(records['buyer'].id,payload,uuid4())

def test_batch_persists_method_and_replays_without_new_stock_or_events(db,records):
    payload=ready(db,records);service=CheckoutService(db);key=uuid4()
    result=service.create(records['buyer'].id,payload,key)
    order_id=int(result['orders'][0].id)
    assert db.get(OrderPayment,order_id).method=='COD'
    assert result['orders'][0].created_at is not None
    notifications=db.scalar(select(func.count()).select_from(Notification))
    assert notifications==4 and records['product'].stock_quantity==4
    assert service.create(records['buyer'].id,payload,key)['orders'][0].id==order_id
    assert db.scalar(select(func.count()).select_from(Notification))==notifications
    payload['sellers'][0]['items'][0]['quantity']=2
    with pytest.raises(IdempotencyConflict):service.create(records['buyer'].id,payload,key)

def test_second_seller_failure_rolls_back_first_seller(db,records):
    payload=ready(db,records)
    user=User(name='Second',email='second@example.test',phone='second',password_hash='test',role='SELLER')
    seller=SellerProfile(user=user,shop_name='Second shop',phone='second',latitude='19.076000',longitude='72.877700',dispatch_location_confirmed_at=datetime.now(timezone.utc))
    product=Product(seller=seller,name='Second item',description='Second',price='20.00',stock_quantity=5,category='Crafts',delivery_radius_km=2,status='APPROVED')
    db.add_all([user,seller,product]);db.flush()
    payload['sellers'].append(dict(seller_id=seller.id,payment_method='COD',items=[dict(product_id=product.id,quantity=1,expected_unit_price='19.00')]))
    count=db.scalar(select(func.count()).select_from(Order))
    with pytest.raises(ProductUnavailable):CheckoutService(db).create(records['buyer'].id,payload,uuid4())
    assert db.scalar(select(func.count()).select_from(Order))==count
    db.refresh(records['product']);assert records['product'].stock_quantity==5
    assert db.scalar(select(func.count()).select_from(OrderPayment))==0
    assert db.scalar(select(func.count()).select_from(Notification))==0

def test_upi_policy_review_snapshots_and_destination_change(db,records):
    payload=ready(db,records);payload['sellers'][0]['payment_method']='UPI'
    settings=Settings(_env_file=None,environment='test',prepaid_upi_enabled=True,approved_refund_policy_reference='SIMULATED-TEST-POLICY-ONLY')
    service=PaymentSettingsService(db,settings)
    admin=User(name='Admin',email='review@example.test',phone='review',password_hash='test',role='ADMIN');db.add(admin);db.flush()
    data=dict(upi_id='synthetic@example',account_holder_name='Synthetic test seller',accept_cod=True,accept_upi=True)
    pending=service.put(records['seller_user'].id,data)
    with pytest.raises(PersistenceConflict):CheckoutService(db,settings).create(records['buyer'].id,payload,uuid4())
    service.review(admin.id,records['seller'].id,dict(status='APPROVED',expected_updated_at=pending['updated_at'],reason='Simulated admin review; no bank verification'))
    no_policy=Settings(_env_file=None,environment='test',prepaid_upi_enabled=True)
    with pytest.raises(PersistenceConflict):CheckoutService(db,no_policy).create(records['buyer'].id,payload,uuid4())
    with pytest.raises(PersistenceConflict):CheckoutService(db).create(records['buyer'].id,payload,uuid4())
    placed=CheckoutService(db,settings).create(records['buyer'].id,payload,uuid4())
    order_id=int(placed['orders'][0].id)
    assert PaymentService(db,settings).instructions(records['buyer'].id,order_id)['available']
    records['seller_user'].is_active=False;db.flush()
    inactive=PaymentService(db,settings).instructions(records['buyer'].id,order_id)
    assert not inactive['available'] and inactive['upi_uri'] is None
    records['seller_user'].is_active=True
    payment=db.get(OrderPayment,order_id);payment.status='SELLER_CONFIRMED';payment.confirmed_at=datetime.now(timezone.utc);db.flush()
    received=PaymentService(db,settings).instructions(records['buyer'].id,order_id)
    assert not received['available'] and received['upi_id'] is None
    payment.status='PENDING';payment.confirmed_at=None;db.flush()
    disabled=PaymentService(db).instructions(records['buyer'].id,order_id)
    assert not disabled['available'] and disabled['upi_id'] is None and disabled['upi_uri'] is None
    data['upi_id']='changed@example';service.put(records['seller_user'].id,data)
    stale=PaymentService(db,settings).instructions(records['buyer'].id,order_id)
    assert not stale['available'] and stale['upi_id'] is None
    with pytest.raises(PersistenceConflict):service.review(admin.id,records['seller'].id,dict(status='APPROVED',expected_updated_at=pending['updated_at'],reason='Stale'))

def test_wishlist_is_owned_deduplicated_and_unavailable_is_private(db,records):
    ready(db,records);service=WishlistService(db);buyer=records['buyer'].id;product=records['product']
    service.put(buyer,product.id,True);service.put(buyer,product.id,True)
    assert service.list(buyer)['count']==1
    assert service.list(buyer)['items'][0]['product'].name==product.name
    product.status='PENDING';db.flush()
    assert service.list(buyer)['items']==[dict(product_id=str(product.id),available=False,product=None)]
    assert product.stock_quantity==5
    stranger=User(name='Buyer two',email='wishlist@example.test',phone='wishlist',password_hash='test',role='BUYER');db.add(stranger);db.flush()
    assert service.list(stranger.id)['count']==0
    service.put(stranger.id,product.id,False)
    assert db.get(WishlistItem,(buyer,product.id)) is not None

def test_wishlist_never_exposes_sellers_without_current_public_consent(db,records):
    from app.schemas.public_discovery import PUBLIC_DISCOVERY_CONSENT_VERSION
    ready(db,records);service=WishlistService(db);seller=records['seller'];product=records['product'];buyer=records['buyer'].id
    seller.public_discovery_confirmed_at=None;seller.public_discovery_latitude=None;seller.public_discovery_longitude=None;seller.public_discovery_consent_version=None;db.flush()
    from app.services.errors import ProductNotFound
    with pytest.raises(ProductNotFound):service.put(buyer,product.id,True)
    seller.public_discovery_latitude=seller.latitude;seller.public_discovery_longitude=seller.longitude
    seller.public_discovery_confirmed_at=datetime.now(timezone.utc);seller.public_discovery_consent_version=PUBLIC_DISCOVERY_CONSENT_VERSION;db.flush()
    service.put(buyer,product.id,True)
    assert service.list(buyer)['items'][0]['product'].name==product.name
    seller.public_discovery_consent_version='withdrawn';db.flush()
    assert service.list(buyer)['items']==[dict(product_id=str(product.id),available=False,product=None)]

def test_public_api_requires_method_but_replays_legacy_order(auth_client,db,records):
    from app.services.orders import OrderService
    from app.services.inputs import OrderPlacement
    payload=ready(db,records);group=payload['sellers'][0]
    legacy=dict(address_id=payload['address_id'],seller_id=group['seller_id'],items=group['items'])
    key=uuid4();headers={**bearer(records['buyer'].id),'Idempotency-Key':str(key)}
    response=auth_client.post('/api/v1/orders',headers=headers,json=legacy)
    assert response.status_code==409
    original=OrderService(db).create(OrderPlacement(buyer_id=records['buyer'].id,idempotency_key=key,**legacy))
    replay=auth_client.post('/api/v1/orders',headers=headers,json=legacy)
    assert replay.status_code==201 and replay.json()['id']==original.id
    assert db.get(OrderPayment,original.id) is None
    changed=auth_client.post('/api/v1/orders',headers=headers,json={**legacy,'payment_method':'COD'})
    assert changed.status_code==409

def test_payment_settings_and_review_api_cannot_be_forged(auth_client,db,records):
    ready(db,records)
    buyer=bearer(records['buyer'].id);seller=bearer(records['seller_user'].id)
    assert auth_client.put('/api/v1/payments/settings',headers=buyer,json={}).status_code==403
    assert auth_client.get('/api/v1/payments/admin/settings',headers=seller).status_code==403
    forged=auth_client.put('/api/v1/payments/settings',headers=seller,json=dict(verification_status='APPROVED',upi_id='synthetic@example'))
    assert forged.status_code==422
    assert auth_client.put('/api/v1/wishlist/'+str(records['product'].id),headers=seller,json=dict(saved=True)).status_code==403
    saved=auth_client.put('/api/v1/wishlist/'+str(records['product'].id),headers=buyer,json=dict(saved=True))
    assert saved.status_code==200 and saved.json()['saved']
    assert auth_client.get('/api/v1/wishlist',headers=buyer).json()['count']==1
