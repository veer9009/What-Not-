"""Separate creative and professional listing categories without changing records."""
from alembic import op
import sqlalchemy as sa

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None

CREATIVE = ('Video Editing', 'Travel Video Editing', 'Influencer Reel Editing', 'VFX', 'Photography', 'Videography', 'Graphic Design', 'Animation and VFX', 'Fashion Design', 'Logo and Branding Design', 'Advertisement Production', 'Promotional Video Production', 'Digital Marketing')
PROFESSIONAL = ('Website Development', 'Mobile Application Development', 'Custom Software Development', 'Portfolio Development', 'E-commerce Development', 'CRM and ERP Solutions', 'AI and Automation', 'Cloud and DevOps', 'Software Maintenance', 'IT Consulting', 'Cybersecurity Services', 'API Development and Integration')
LEGACY = CREATIVE[:4]

def quoted(values):
    return ','.join("'{}'".format(value.replace("'", "''")) for value in values)

def upgrade():
    op.add_column('creative_listings', sa.Column('domain', sa.String(12), nullable=False, server_default='CREATIVE'))
    op.drop_constraint(op.f('ck_creative_listings_category'), 'creative_listings', type_='check')
    op.create_check_constraint('category', 'creative_listings', "(domain='CREATIVE' AND category IN ({})) OR (domain='PROFESSIONAL' AND category IN ({}))".format(quoted(CREATIVE), quoted(PROFESSIONAL)))

def downgrade():
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE creative_listings IN ACCESS EXCLUSIVE MODE'))
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM creative_listings WHERE domain <> 'CREATIVE' OR category NOT IN ({}))".format(quoted(LEGACY)))):
        raise RuntimeError('Cannot downgrade while professional or new creative categories exist')
    op.drop_constraint(op.f('ck_creative_listings_category'), 'creative_listings', type_='check')
    op.create_check_constraint('category', 'creative_listings', 'category IN ({})'.format(quoted(LEGACY)))
    op.drop_column('creative_listings', 'domain')
