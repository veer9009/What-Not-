"""Require intentional dispatch-location confirmation without rewriting coordinates."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('seller_profiles', sa.Column('dispatch_location_confirmed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('seller_profiles', 'dispatch_location_confirmed_at')
