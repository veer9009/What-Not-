"""Require buyer confirmation after seller handover; preserve historical delivery."""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

OLD_STATUSES = "'PLACED','ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','CANCELLED','REJECTED'"
NEW_STATUSES = OLD_STATUSES + ",'AWAITING_BUYER_CONFIRMATION'"


def upgrade():
    op.alter_column('orders', 'status', existing_type=sa.String(20), type_=sa.String(32), existing_nullable=False)
    op.drop_constraint(op.f('ck_orders_status'), 'orders', type_='check')
    op.create_check_constraint(op.f('ck_orders_status'), 'orders', f'status IN ({NEW_STATUSES})')


def downgrade():
    # Prevent a concurrent handover between the preflight check and schema change.
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE orders IN ACCESS EXCLUSIVE MODE'))
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM orders WHERE status='AWAITING_BUYER_CONFIRMATION')")):
        raise RuntimeError('Cannot downgrade while orders are awaiting buyer confirmation; resolve them through the current application first.')
    op.drop_constraint(op.f('ck_orders_status'), 'orders', type_='check')
    op.create_check_constraint(op.f('ck_orders_status'), 'orders', f'status IN ({OLD_STATUSES})')
    op.alter_column('orders', 'status', existing_type=sa.String(32), type_=sa.String(20), existing_nullable=False)
