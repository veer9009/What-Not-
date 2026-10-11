"""Initial What Not? marketplace persistence foundation.

Revision ID: 0001
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def identifier():
    return sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False)


def timestamps(updated=True):
    columns = [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)]
    if updated:
        columns.append(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    return columns


def check(expression, name):
    return sa.CheckConstraint(expression, name=op.f(name))


def upgrade():
    op.create_table("users", identifier(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
        check("role IN ('BUYER','SELLER','ADMIN')", "ck_users_role"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("phone", name=op.f("uq_users_phone")))
    op.create_table("seller_profiles", identifier(),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("shop_name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        *timestamps(),
        check("latitude BETWEEN -90 AND 90", "ck_seller_profiles_latitude"),
        check("longitude BETWEEN -180 AND 180", "ck_seller_profiles_longitude"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_seller_profiles_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seller_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_seller_profiles_user_id")))
    op.create_table("products", identifier(),
        sa.Column("seller_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("delivery_radius_km", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(10), server_default="PENDING", nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
        check("price >= 0 AND price != 'NaN'::numeric", "ck_products_price"),
        check("stock_quantity >= 0", "ck_products_stock_quantity"),
        check("delivery_radius_km IN (1,2,3)", "ck_products_delivery_radius_km"),
        check("status IN ('PENDING','APPROVED','REJECTED')", "ck_products_status"),
        sa.ForeignKeyConstraint(["seller_id"], ["seller_profiles.id"], ondelete="RESTRICT", name=op.f("fk_products_seller_id_seller_profiles")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("id", "seller_id", name="uq_products_id_seller_id"))
    op.create_index("ix_products_seller_id", "products", ["seller_id"])
    op.create_table("product_images", identifier(),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        *timestamps(updated=False),
        check("sort_order >= 0", "ck_product_images_sort_order"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE", name=op.f("fk_product_images_product_id_products")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_images")))
    op.create_index("ix_product_images_product_sort", "product_images", ["product_id", "sort_order"])
    op.create_index("uq_product_images_primary", "product_images", ["product_id"], unique=True, postgresql_where=sa.text("is_primary"))
    op.create_table("addresses", identifier(),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("address_line1", sa.String(255), nullable=False),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("state", sa.String(120), nullable=False),
        sa.Column("pincode", sa.String(20), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        *timestamps(),
        check("latitude BETWEEN -90 AND 90", "ck_addresses_latitude"),
        check("longitude BETWEEN -180 AND 180", "ck_addresses_longitude"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_addresses_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_addresses")))
    op.create_index("ix_addresses_user_id", "addresses", ["user_id"])
    op.create_index("uq_addresses_default", "addresses", ["user_id"], unique=True, postgresql_where=sa.text("is_default"))
    op.create_table("orders", identifier(),
        sa.Column("buyer_id", sa.BigInteger(), nullable=False),
        sa.Column("seller_id", sa.BigInteger(), nullable=False),
        sa.Column("address_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), server_default="PLACED", nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        *timestamps(),
        check("status IN ('PLACED','ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','CANCELLED','REJECTED')", "ck_orders_status"),
        check("subtotal >= 0 AND subtotal != 'NaN'::numeric", "ck_orders_subtotal"),
        check("delivery_fee >= 0 AND delivery_fee != 'NaN'::numeric", "ck_orders_delivery_fee"),
        check("total_amount >= 0 AND total_amount != 'NaN'::numeric", "ck_orders_total_amount"),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_orders_buyer_id_users")),
        sa.ForeignKeyConstraint(["seller_id"], ["seller_profiles.id"], ondelete="RESTRICT", name=op.f("fk_orders_seller_id_seller_profiles")),
        sa.ForeignKeyConstraint(["address_id"], ["addresses.id"], ondelete="RESTRICT", name=op.f("fk_orders_address_id_addresses")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("id", "seller_id", name="uq_orders_id_seller_id"))
    for name in ("buyer_id", "seller_id", "address_id"):
        op.create_index(f"ix_orders_{name}", "orders", [name])
    op.create_table("order_items", identifier(),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("seller_id", sa.BigInteger(), nullable=False),
        sa.Column("product_name", sa.String(120), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        check("quantity > 0", "ck_order_items_quantity"),
        check("unit_price >= 0 AND unit_price != 'NaN'::numeric", "ck_order_items_unit_price"),
        sa.ForeignKeyConstraint(["order_id", "seller_id"], ["orders.id", "orders.seller_id"], ondelete="CASCADE", name="fk_order_items_order_seller"),
        sa.ForeignKeyConstraint(["product_id", "seller_id"], ["products.id", "products.seller_id"], ondelete="RESTRICT", name="fk_order_items_product_seller"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
        sa.UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"))
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"])


def downgrade():
    # Drop children first; table removal also removes their indexes and constraints.
    for table in ("order_items", "orders", "addresses", "product_images", "products", "seller_profiles", "users"):
        op.drop_table(table)
