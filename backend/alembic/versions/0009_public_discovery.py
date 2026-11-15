"""Explicitly consented public discovery point; never backfill private dispatch."""
from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('seller_profiles', sa.Column('public_discovery_latitude', sa.Numeric(9, 6)))
    op.add_column('seller_profiles', sa.Column('public_discovery_longitude', sa.Numeric(9, 6)))
    op.add_column('seller_profiles', sa.Column('public_discovery_confirmed_at', sa.DateTime(timezone=True)))
    op.add_column('seller_profiles', sa.Column('public_discovery_consent_version', sa.String(32)))
    op.create_check_constraint('public_discovery_latitude', 'seller_profiles',
                               'public_discovery_latitude BETWEEN -90 AND 90')
    op.create_check_constraint('public_discovery_longitude', 'seller_profiles',
                               'public_discovery_longitude BETWEEN -180 AND 180')
    op.create_check_constraint('public_discovery_fields', 'seller_profiles', """
        (public_discovery_latitude IS NULL AND public_discovery_longitude IS NULL
         AND public_discovery_confirmed_at IS NULL AND public_discovery_consent_version IS NULL)
        OR (public_discovery_latitude IS NOT NULL AND public_discovery_longitude IS NOT NULL
            AND public_discovery_confirmed_at IS NOT NULL AND public_discovery_consent_version IS NOT NULL
            AND length(trim(public_discovery_consent_version)) > 0)""")


def downgrade():
    raise RuntimeError('Public-point consent history requires a separately reviewed recovery procedure; no automatic downgrade.')
