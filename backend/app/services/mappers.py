"""Explicit API/storage mappings; use while the session is open."""
from app.schemas.product import ProductResponse
from app.schemas.order import OrderResponse, OrderItemResponse
from app.schemas.user import PublicUserResponse


def user_response(user):
    return PublicUserResponse(id=user.id, name=user.name, email=user.email, role=user.role)


def product_response(product):
    primary = next((image.image_url for image in product.images if image.is_primary), None)
    return ProductResponse(id=product.id, seller_id=product.seller_id, name=product.name,
        description=product.description, price=product.price, stock_quantity=product.stock_quantity,
        category=product.category, delivery_radius_km=product.delivery_radius_km,
        image_url=primary, status=product.status, rejection_reason=product.rejection_reason,
        is_active=product.is_active)


def order_response(order):
    return OrderResponse(id=order.id, buyer_id=order.buyer_id, seller_id=order.seller_id,
        status=order.status, subtotal=order.subtotal, delivery_fee=order.delivery_fee,
        total=order.total_amount, items=[OrderItemResponse(product_id=item.product_id,
            seller_id=item.seller_id, name=item.product_name, quantity=item.quantity,
            unit_price=item.unit_price) for item in sorted(order.items, key=lambda item: item.product_id)])
