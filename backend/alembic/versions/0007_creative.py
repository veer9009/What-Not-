"""Separate creative providers, moderated services and buyer-confirmed engagements."""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

def ident(): return sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True)
def created(): return sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
def updated(): return sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
def fk(name, target, unique=False): return sa.Column(name, sa.BigInteger(), sa.ForeignKey(target, ondelete='RESTRICT'), nullable=False, unique=unique)

def upgrade():
    op.create_table('creative_providers', ident(), created(), updated(), fk('user_id','users.id',True), sa.Column('display_name',sa.String(120),nullable=False), sa.Column('bio',sa.Text(),nullable=False))
    op.create_table('creative_listings', ident(), created(), updated(), fk('provider_id','creative_providers.id'),
        sa.Column('title',sa.String(120),nullable=False), sa.Column('description',sa.Text(),nullable=False), sa.Column('category',sa.String(40),nullable=False),
        sa.Column('pricing',sa.String(12),nullable=False), sa.Column('amount',sa.Numeric(12,2)), sa.Column('currency',sa.String(3),nullable=False),
        sa.Column('remote',sa.Boolean(),nullable=False), sa.Column('locality',sa.String(160)), sa.Column('portfolio',sa.JSON(),nullable=False),
        sa.Column('status',sa.String(12),nullable=False), sa.Column('rejection_reason',sa.String(1000)), sa.Column('is_active',sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','TAKEN_DOWN')",name='status'), sa.CheckConstraint("pricing IN ('FIXED','STARTING','HOURLY','QUOTATION')",name='pricing'),
        sa.CheckConstraint("(pricing='QUOTATION' AND amount IS NULL) OR (pricing<>'QUOTATION' AND amount IS NOT NULL AND amount>0)",name='amount'), sa.CheckConstraint("category IN ('Video Editing','Travel Video Editing','Influencer Reel Editing','VFX')",name='category'), sa.CheckConstraint("currency='INR'",name='currency'),sa.CheckConstraint('remote OR locality IS NOT NULL',name='service_area'))
    op.create_table('creative_rfqs',ident(),created(),fk('listing_id','creative_listings.id'),fk('buyer_id','users.id'),sa.Column('brief',sa.Text(),nullable=False),sa.Column('request_key',sa.String(36),nullable=False),sa.Column('request_fingerprint',sa.String(64),nullable=False),sa.UniqueConstraint('buyer_id','listing_id','request_key',name='uq_creative_rfqs_request'))
    op.create_table('creative_responses',ident(),created(),fk('rfq_id','creative_rfqs.id'),sa.Column('terms',sa.Text(),nullable=False),sa.Column('amount',sa.Numeric(12,2),nullable=False),sa.Column('currency',sa.String(3),nullable=False),sa.CheckConstraint("amount>0 AND currency='INR'",name='quote'),sa.Column('request_key',sa.String(36),nullable=False),sa.Column('request_fingerprint',sa.String(64),nullable=False),sa.UniqueConstraint('rfq_id','request_key',name='uq_creative_responses_request'))
    op.create_table('creative_engagements',ident(),created(),updated(),fk('rfq_id','creative_rfqs.id',True),fk('response_id','creative_responses.id',True),fk('buyer_id','users.id'),fk('provider_id','creative_providers.id'),
        sa.Column('title',sa.String(120),nullable=False),sa.Column('terms',sa.Text(),nullable=False),sa.Column('amount',sa.Numeric(12,2),nullable=False),sa.Column('currency',sa.String(3),nullable=False),sa.Column('status',sa.String(12),nullable=False),sa.Column('delivered_at',sa.DateTime(timezone=True)),sa.Column('completed_at',sa.DateTime(timezone=True)),sa.CheckConstraint("status IN ('ACCEPTED','DELIVERED','COMPLETED')",name='status'))
    op.create_table('creative_reviews',ident(),created(),fk('engagement_id','creative_engagements.id',True),fk('buyer_id','users.id'),sa.Column('rating',sa.Integer(),nullable=False),sa.Column('text',sa.Text(),nullable=False),sa.CheckConstraint('rating BETWEEN 1 AND 5',name='rating'))
    for table, columns in {'creative_listings':['provider_id','status'],'creative_rfqs':['listing_id','buyer_id'],'creative_responses':['rfq_id'],'creative_engagements':['buyer_id','provider_id']}.items():
        for column in columns: op.create_index(f'ix_{table}_{column}',table,[column])

def downgrade():
    connection = op.get_bind()
    tables = ['creative_reviews','creative_engagements','creative_responses','creative_rfqs','creative_listings','creative_providers']
    connection.execute(sa.text('LOCK TABLE '+', '.join(tables)+' IN ACCESS EXCLUSIVE MODE'))
    if any(connection.scalar(sa.text(f'SELECT EXISTS (SELECT 1 FROM {table})')) for table in tables):
        raise RuntimeError('Cannot remove creative records; preserve accepted terms and buyer history')
    for table in tables: op.drop_table(table)
