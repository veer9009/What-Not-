"""Seller-reviewed payment settings, atomic checkout and saved products."""
from alembic import op
import sqlalchemy as sa
revision='0015'
down_revision='0014'
branch_labels=None
depends_on=None

def upgrade():
    from app.models.shopping import SellerPaymentSettings, WishlistItem, CheckoutBatch
    bind=op.get_bind()
    for table in (SellerPaymentSettings.__table__, WishlistItem.__table__, CheckoutBatch.__table__):
        table.create(bind)
    op.add_column('order_payments',sa.Column('destination_upi_id',sa.String(255),nullable=True))
    op.add_column('order_payments',sa.Column('destination_name',sa.String(120),nullable=True))
    op.add_column('order_payments',sa.Column('destination_revision',sa.Integer(),nullable=True))

def downgrade():
    bind=op.get_bind()
    # Keep concurrent writers out between the history check and destructive DDL.
    bind.execute(sa.text('LOCK TABLE order_payments, seller_payment_settings, wishlist_items, checkout_batches IN ACCESS EXCLUSIVE MODE'))
    if any(bind.scalar(sa.text('SELECT EXISTS (SELECT 1 FROM '+table+')')) for table in ('checkout_batches','wishlist_items','seller_payment_settings')) or bind.scalar(sa.text('SELECT EXISTS (SELECT 1 FROM order_payments WHERE destination_revision IS NOT NULL)')):
        raise RuntimeError('Shopping and payment destination history must be explicitly archived before downgrade')
    for column in ('destination_revision','destination_name','destination_upi_id'):
        op.drop_column('order_payments',column)
    for table in ('checkout_batches','wishlist_items','seller_payment_settings'):
        op.drop_table(table)
