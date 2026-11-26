from sqlalchemy import select
from app.models import Product, SellerProfile, User
from app.models.shopping import WishlistItem
from app.schemas.discovery import BuyerProduct
from app.services.users import require_user
from app.services.operations import write_operation
from app.services.errors import ProductNotFound
from app.services.mappers import safe_product_image_url
from app.services.discovery import has_current_public_consent

class WishlistService:
    def __init__(self,session,settings=None):self.session=session;self.settings=settings
    def _product(self,product_id):
        product=self.session.scalar(select(Product).join(SellerProfile).join(User,SellerProfile.user_id==User.id).where(Product.id==product_id,Product.status=='APPROVED',Product.is_active.is_(True),User.is_active.is_(True),User.role=='SELLER',SellerProfile.dispatch_location_confirmed_at.is_not(None)))
        return product if product is not None and has_current_public_consent(product.seller) else None
    def list(self,buyer_id):
        require_user(self.session,buyer_id,role='BUYER');items=[]
        for row in self.session.scalars(select(WishlistItem).where(WishlistItem.buyer_id==buyer_id).order_by(WishlistItem.created_at.desc(),WishlistItem.product_id)):
            product=self._product(row.product_id);view=None
            if product:
                seller=product.seller
                view=BuyerProduct(id=product.id,seller_id=product.seller_id,name=product.name,description=product.description,price=product.price,stock_quantity=product.stock_quantity,category=product.category,delivery_radius_km=product.delivery_radius_km,image_url=safe_product_image_url(next((i.image_url for i in product.images if i.is_primary),None),self.settings),shop_name=seller.shop_name,is_verified=seller.is_verified)
            items.append(dict(product_id=str(row.product_id),available=product is not None,product=view))
        return dict(items=items,count=len(items))
    @write_operation
    def put(self,buyer_id,product_id,saved):
        require_user(self.session,buyer_id,role='BUYER',lock=True)
        row=self.session.get(WishlistItem,(buyer_id,product_id))
        if saved and row is None:
            if self._product(product_id) is None:raise ProductNotFound('Product is unavailable')
            self.session.add(WishlistItem(buyer_id=buyer_id,product_id=product_id))
        elif not saved and row is not None:self.session.delete(row)
        return dict(saved=saved)
