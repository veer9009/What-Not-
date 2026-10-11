import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DataError


@pytest.mark.parametrize("table,column,value", [
    ("users", "role", "VISITOR"),
    ("products", "delivery_radius_km", 0), ("products", "delivery_radius_km", 4),
    ("products", "stock_quantity", -1), ("products", "status", "VISIBLE"),
    ("products", "price", "-0.01"), ("products", "price", "NaN"),
    ("orders", "status", "PAID"), ("orders", "subtotal", "-0.01"),
    ("orders", "delivery_fee", "-0.01"), ("orders", "total_amount", "-0.01"),
    ("orders", "total_amount", "NaN"), ("order_items", "unit_price", "-0.01"),
    ("orders", "subtotal", "NaN"), ("orders", "delivery_fee", "NaN"),
    ("order_items", "unit_price", "NaN"),
    ("order_items", "quantity", 0), ("order_items", "quantity", -1),
    ("seller_profiles", "latitude", "90.000001"), ("seller_profiles", "longitude", "-180.000001"),
    ("addresses", "latitude", "-90.000001"), ("addresses", "longitude", "180.000001"),
    ("seller_profiles", "latitude", "-90.000001"), ("seller_profiles", "longitude", "180.000001"),
    ("addresses", "latitude", "90.000001"), ("addresses", "longitude", "-180.000001"),
])
def test_invalid_values_are_rejected(db, records, table, column, value):
    # Identifiers come only from the fixed test cases above; values stay parameterized.
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(text(f"UPDATE {table} SET {column}=:value"), {"value": value})


@pytest.mark.parametrize("column", ["email", "phone"])
def test_user_contact_uniqueness(db, records, column):
    value = getattr(records["buyer"], column)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(text(f"UPDATE users SET {column}=:value WHERE id=:id"),
                       {"value": value, "id": records["seller_user"].id})


def test_one_profile_per_user(db, records):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(text("INSERT INTO seller_profiles(user_id,shop_name,phone,latitude,longitude) "
                            "VALUES (:user,'Another shop','123',0,0)"), {"user": records["seller_user"].id})


def test_order_item_cannot_cross_sellers(db, records):
    seller = db.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) "
                            "VALUES ('Other','other@example.test','other','hash','SELLER') RETURNING id"))
    profile = db.scalar(text("INSERT INTO seller_profiles(user_id,shop_name,phone,latitude,longitude) "
                             "VALUES (:user,'Other','other',0,0) RETURNING id"), {"user": seller})
    product = db.scalar(text("INSERT INTO products(seller_id,name,description,price,stock_quantity,category,delivery_radius_km) "
                             "VALUES (:seller,'Other product','Other',10,1,'Crafts',1) RETURNING id"), {"seller": profile})
    # Changing only product violates product+seller FK; changing both violates order+seller FK.
    for seller_id in (records["seller"].id, profile):
        with pytest.raises(IntegrityError):
            with db.begin_nested():
                db.execute(text("UPDATE order_items SET product_id=:product,seller_id=:seller"),
                           {"product": product, "seller": seller_id})


def test_primary_image_and_sort_order(db, records):
    from app.models import ProductImage
    image = ProductImage(product=records["product"], image_url="https://example.test/vase.jpg",
                         is_primary=True, sort_order=0)
    db.add(image)
    db.flush()
    assert records["product"].images == [image]
    for primary, sort in [(True, 1), (False, -1)]:
        with pytest.raises(IntegrityError):
            with db.begin_nested():
                db.execute(text("INSERT INTO product_images(product_id,image_url,is_primary,sort_order) "
                                "VALUES (:product,'https://example.test/other.jpg',:primary,:sort)"),
                           {"product": records["product"].id, "primary": primary, "sort": sort})
    db.execute(text("INSERT INTO product_images(product_id,image_url,is_primary,sort_order) "
                    "VALUES (:product,'https://example.test/extra.jpg',false,1)"), {"product": records["product"].id})


def test_one_default_address(db, records):
    db.execute(text("UPDATE addresses SET is_default=true"))
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(text("INSERT INTO addresses(user_id,label,address_line1,city,state,pincode,latitude,longitude,is_default) "
                            "VALUES (:user,'Work','2 Lane','Mumbai','Maharashtra','400001',0,0,true)"),
                       {"user": records["buyer"].id})


def test_referenced_product_cannot_be_deleted(db, records):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(text("DELETE FROM products WHERE id=:id"), {"id": records["product"].id})


def test_zero_money_is_allowed_and_precision_is_bounded(db, records):
    db.execute(text("UPDATE products SET price=0"))
    with pytest.raises(DataError):
        with db.begin_nested():
            db.execute(text("UPDATE products SET price=10000000000.00"))


@pytest.mark.parametrize("status", ["PLACED", "ACCEPTED", "PREPARING", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED", "REJECTED"])
def test_valid_order_statuses(db, records, status):
    db.execute(text("UPDATE orders SET status=:status"), {"status": status})


@pytest.mark.parametrize("radius", [1, 2, 3])
def test_valid_product_radii(db, records, radius):
    db.execute(text("UPDATE products SET delivery_radius_km=:radius"), {"radius": radius})


@pytest.mark.parametrize("table,column", [
    ("seller_profiles", "user_id"), ("products", "seller_id"), ("addresses", "user_id"),
    ("orders", "buyer_id"), ("orders", "seller_id"), ("orders", "address_id"),
    ("order_items", "order_id"), ("order_items", "product_id"),
])
def test_missing_parent_is_rejected(db, records, table, column):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(text(f"UPDATE {table} SET {column}=9223372036854775807"))


def test_duplicate_product_in_order_is_rejected(db, records):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(text("INSERT INTO order_items(order_id,product_id,seller_id,product_name,quantity,unit_price) "
                            "SELECT order_id,product_id,seller_id,product_name,quantity,unit_price FROM order_items"))


def test_image_deletion_cascade(db, records):
    # Use an unpurchased product so the history-protection FK does not block deletion.
    product = db.scalar(text("INSERT INTO products(seller_id,name,description,price,stock_quantity,category,delivery_radius_km) "
                             "VALUES (:seller,'Draft','Draft',0,0,'Crafts',1) RETURNING id"), {"seller": records["seller"].id})
    db.execute(text("INSERT INTO product_images(product_id,image_url) VALUES (:product,'https://example.test/draft.jpg')"),
               {"product": product})
    db.execute(text("DELETE FROM products WHERE id=:product"), {"product": product})
    assert db.scalar(text("SELECT count(*) FROM product_images WHERE product_id=:product"), {"product": product}) == 0
