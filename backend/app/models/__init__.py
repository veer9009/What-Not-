"""Import all mappings before Alembic examines Base.metadata."""
from app.models.user import User
from app.models.seller_profile import SellerProfile
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.address import Address
from app.models.order import Order
from app.models.order_item import OrderItem

__all__ = ["User", "SellerProfile", "Product", "ProductImage", "Address", "Order", "OrderItem"]
