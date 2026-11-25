"""Add direct-payment attestations without changing or backfilling orders."""
from alembic import op
import sqlalchemy as sa

revision='0013'
down_revision='0012'
branch_labels=None
depends_on=None

# Keep migration definitions independent of mutable application models.
CHECKS={
    'method': "method IN ('COD','UPI')",
    'status': "status IN ('PENDING','BUYER_REPORTED','SELLER_CONFIRMED')",
    'reference': "reference IS NULL OR (method='UPI' AND reference ~ '^[A-Za-z0-9][A-Za-z0-9 _./-]{0,99}$')",
    'reported_method': "method='UPI' OR reported_at IS NULL",
    'state_dates': "(status='PENDING' AND reported_at IS NULL AND confirmed_at IS NULL) OR "
                   "(status='BUYER_REPORTED' AND reported_at IS NOT NULL AND confirmed_at IS NULL) OR "
                   "(status='SELLER_CONFIRMED' AND confirmed_at IS NOT NULL)",
    'reference_report': 'reference IS NULL OR reported_at IS NOT NULL',
}


def upgrade():
    op.create_table('order_payments',sa.Column('order_id',sa.BigInteger(),nullable=False),
        sa.Column('method',sa.String(3),nullable=False),sa.Column('status',sa.String(24),nullable=False),
        sa.Column('reference',sa.String(100)),sa.Column('reported_at',sa.DateTime(timezone=True)),
        sa.Column('confirmed_at',sa.DateTime(timezone=True)),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('order_id'),sa.ForeignKeyConstraint(['order_id'],['orders.id'],ondelete='RESTRICT'),
        *(sa.CheckConstraint(sql,name=op.f('ck_order_payments_'+name)) for name,sql in CHECKS.items()))


def downgrade():
    op.execute('LOCK TABLE order_payments IN ACCESS EXCLUSIVE MODE')
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM order_payments) THEN
        RAISE EXCEPTION 'Refusing downgrade with payment history'; END IF; END $$""")
    op.drop_table('order_payments')
