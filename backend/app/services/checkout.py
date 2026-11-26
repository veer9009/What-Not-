from hashlib import sha256
import json
from decimal import Decimal
from app.models import Order, SellerProfile, Product
from app.models.shopping import CheckoutBatch
from app.schemas.checkout import CheckoutInput
from app.services.inputs import OrderPlacement
from app.services.orders import OrderService
from app.services.payment_settings import PaymentSettingsService
from app.services.operations import write_operation
from app.services.errors import IdempotencyConflict, PersistenceConflict
from app.services.users import require_user
from app.services.mappers import order_response, safe_product_image_url
from app.repositories.orders import OrderRepository

class CheckoutService:
    def __init__(self,session,settings=None):self.session=session;self.settings=settings
    def _image(self,product_id):
        product=self.session.get(Product,product_id)
        return safe_product_image_url(next((image.image_url for image in product.images if image.is_primary),None),self.settings)
    def _orders(self,buyer_id,data,preview=False):
        service=OrderService(self.session,settings=self.settings,require_price_confirmation=True)
        return [service.create(OrderPlacement(buyer_id=buyer_id,address_id=data.address_id,seller_id=g.seller_id,items=g.items,payment_method=None if preview else g.payment_method),validate_only=preview) for g in sorted(data.sellers,key=lambda g:g.seller_id)]
    def preview(self,buyer_id,data):
        data=CheckoutInput.model_validate(data);groups=[]
        for order in self._orders(buyer_id,data,True):
            seller=self.session.get(SellerProfile,order.seller_id)
            service=PaymentSettingsService(self.session,self.settings);row=service.row(seller.id);reason=service.reason(row)
            methods=(['COD'] if not row or row.accept_cod else [])+(['UPI'] if reason is None else [])
            groups.append(dict(seller_id=str(seller.id),seller_name=seller.shop_name,items=[dict(product_id=str(i.product_id),name=i.product_name,quantity=i.quantity,unit_price=format(i.unit_price,'.2f'),image_url=self._image(i.product_id)) for i in order.items],subtotal=format(order.subtotal,'.2f'),delivery_fee=format(order.delivery_fee,'.2f'),total=format(order.total_amount,'.2f'),available_payment_methods=methods,upi_unavailable_reason=reason))
        return dict(groups=groups,total=format(sum((Decimal(g['total']) for g in groups),Decimal('0.00')),'.2f'),currency='INR')
    @write_operation
    def create(self,buyer_id,data,key):
        data=CheckoutInput.model_validate(data);require_user(self.session,buyer_id,role='BUYER',lock=True)
        logical=data.model_dump(mode='json');logical['sellers']=sorted(logical['sellers'],key=lambda g:g['seller_id'])
        for g in logical['sellers']:g['items']=sorted(g['items'],key=lambda i:i['product_id'])
        fingerprint=sha256(json.dumps(logical,sort_keys=True).encode()).hexdigest()
        OrderRepository(self.session).lock_idempotency(buyer_id,'checkout:'+str(key))
        batch=self.session.get(CheckoutBatch,(buyer_id,str(key)))
        if batch:
            if batch.fingerprint!=fingerprint:raise IdempotencyConflict('Checkout key was used for another request')
            return dict(orders=[order_response(self.session.get(Order,int(i))) for i in batch.order_ids])
        if any(g.payment_method is None for g in data.sellers):raise PersistenceConflict('Select a payment method for every seller')
        rows=self._orders(buyer_id,data)
        self.session.add(CheckoutBatch(buyer_id=buyer_id,key=str(key),fingerprint=fingerprint,order_ids=[str(o.id) for o in rows]))
        return dict(orders=[order_response(o) for o in rows])
