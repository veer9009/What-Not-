"""Buyer-scoped idempotency on order placement; preserve legacy orders."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('idempotency_key', sa.Uuid(), nullable=True))
    op.add_column('orders', sa.Column('request_fingerprint', sa.String(64), nullable=True))
    op.create_unique_constraint('uq_orders_buyer_id_idempotency_key', 'orders', ['buyer_id', 'idempotency_key'])
    op.create_check_constraint(op.f('ck_orders_idempotency_pair'), 'orders',
        '(idempotency_key IS NULL AND request_fingerprint IS NULL) OR '
        '(idempotency_key IS NOT NULL AND request_fingerprint IS NOT NULL)')


def downgrade():
    op.drop_constraint(op.f('ck_orders_idempotency_pair'), 'orders', type_='check')
    op.drop_constraint('uq_orders_buyer_id_idempotency_key', 'orders', type_='unique')
    op.drop_column('orders', 'request_fingerprint')
    op.drop_column('orders', 'idempotency_key')
