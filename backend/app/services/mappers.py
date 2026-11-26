"""Explicit API/storage mappings; use while the session is open."""
from app.schemas.product import ProductResponse, ProductImageResponse
from app.schemas.order import OrderResponse, OrderItemResponse
from app.schemas.user import PublicUserResponse
from app.schemas.product import ImageURL
from pydantic import TypeAdapter, ValidationError

_image_url = TypeAdapter(ImageURL)


def safe_product_image_url(value, settings=None):
    """Legacy rows must not disclose URL credentials or break an entire listing read."""
    if value is None:
        return None
    if value.startswith('whatnot-upload:'):
        if settings is None:
            return None
        from app.services.product_images import signed_image_url
        return signed_image_url(value, settings)
    try:
        return _image_url.validate_python(value)
    except ValidationError:
        return None


def user_response(user):
    return PublicUserResponse(id=user.id, name=user.name, email=user.email, role=user.role)


def product_response(product, settings=None):
    images = [ProductImageResponse(id=image.id,image_url=url,is_primary=image.is_primary,sort_order=image.sort_order)
              for image in product.images if (url := safe_product_image_url(image.image_url, settings)) is not None]
    primary = next((image.image_url for image in images if image.is_primary), None)
    return ProductResponse(id=product.id, seller_id=product.seller_id, name=product.name,
        description=product.description, price=product.price, stock_quantity=product.stock_quantity,
        category=product.category, delivery_radius_km=product.delivery_radius_km,
        image_url=primary, status=product.status, rejection_reason=product.rejection_reason,
        images=images,
        is_active=product.is_active,updated_at=product.updated_at)


def order_response(order):
    from sqlalchemy.orm import object_session
    from app.models.payment import OrderPayment
    session=object_session(order)
    payment=session.get(OrderPayment,order.id) if session else None
    return OrderResponse(created_at=order.created_at,payment_method=payment.method if payment else None,id=order.id, buyer_id=order.buyer_id, seller_id=order.seller_id,
        status=order.status, subtotal=order.subtotal, delivery_fee=order.delivery_fee,
        delivered_at=order.delivered_at, confirmation_deadline=order.confirmation_deadline,
        completed_at=order.completed_at, completion_source=order.completion_source,
        total=order.total_amount, items=[OrderItemResponse(product_id=item.product_id,
            seller_id=item.seller_id, name=item.product_name, quantity=item.quantity,
            unit_price=item.unit_price) for item in sorted(order.items, key=lambda item: item.product_id)])
