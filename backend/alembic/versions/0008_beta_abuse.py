"""Durable pseudonymous request quotas; account verification timestamps."""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('request_quotas',
        sa.Column('scope_hash', sa.String(64), primary_key=True),
        sa.Column('window_start', sa.BigInteger(), primary_key=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.CheckConstraint('attempts > 0', name='attempts'))
    op.create_index('ix_request_quotas_window_start', 'request_quotas', ['window_start'])
    op.add_column('users', sa.Column('phone_verified_at', sa.DateTime(timezone=True)))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True)))


def downgrade():
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE users, request_quotas IN ACCESS EXCLUSIVE MODE'))
    if connection.scalar(sa.text('SELECT EXISTS(SELECT 1 FROM users WHERE phone_verified_at IS NOT NULL OR email_verified_at IS NOT NULL)')):
        raise RuntimeError('Cannot downgrade while verified account evidence exists; preserve verification history.')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'phone_verified_at')
    op.drop_table('request_quotas')
