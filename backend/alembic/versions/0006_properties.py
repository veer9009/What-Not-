"""Sale-only properties and private appointment workflows."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None

def base():
    return [sa.Column('id',sa.BigInteger(),primary_key=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now())]
def fk(name,table): return sa.Column(name,sa.BigInteger(),sa.ForeignKey(table+'.id'),nullable=False)
def upgrade():
    op.create_table('property_profiles',*base(),fk('user_id','users'),sa.Column('display_name',sa.String(120),nullable=False),sa.Column('capacity',sa.String(10),nullable=False),sa.Column('share_contact',sa.Boolean(),nullable=False),sa.UniqueConstraint('user_id'),sa.CheckConstraint("capacity IN ('OWNER','AGENT')",name='capacity'))
    op.create_table('property_listings',*base(),fk('creator_id','users'),sa.Column('title',sa.String(160),nullable=False),sa.Column('description',sa.Text(),nullable=False),sa.Column('category',sa.String(30),nullable=False),sa.Column('price',sa.Numeric(12,2),nullable=False),sa.Column('locality',sa.String(120),nullable=False),sa.Column('private_address',sa.Text(),nullable=False),sa.Column('status',sa.String(12),nullable=False),sa.Column('rejection_reason',sa.Text()),sa.Column('reconfirmed_at',sa.DateTime(timezone=True),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','SOLD','HIDDEN')",name='status'),sa.CheckConstraint('price > 0',name='positive_price'),sa.CheckConstraint("category IN ('Residential','Commercial','Land/Plots')",name='category'))
    op.add_column('property_listings',sa.Column('capacity',sa.String(10),nullable=False))
    op.create_table('property_enquiries',*base(),fk('property_id','property_listings'),fk('buyer_id','users'),sa.Column('message',sa.Text(),nullable=False),sa.Column('response',sa.Text()),sa.Column('status',sa.String(12),nullable=False))
    op.create_table('property_visits',*base(),fk('property_id','property_listings'),fk('buyer_id','users'),sa.Column('scheduled_at',sa.DateTime(timezone=True),nullable=False),sa.Column('status',sa.String(12),nullable=False),sa.Column('reason',sa.Text()),sa.CheckConstraint("status IN ('PENDING','ALTERNATE','CONFIRMED','REJECTED','CANCELLED','SUSPENDED')",name='status'))
    op.create_table('saved_properties',*base(),fk('buyer_id','users'),fk('property_id','property_listings'),sa.UniqueConstraint('buyer_id','property_id'))
    op.create_table('property_reports',*base(),fk('property_id','property_listings'),fk('reporter_id','users'),sa.Column('reason',sa.String(40),nullable=False),sa.Column('explanation',sa.Text(),nullable=False),sa.Column('disposition',sa.String(12),nullable=False),sa.Column('resolution_reason',sa.Text()))
    for table,columns in {'property_listings':['creator_id','status','expires_at'],'property_enquiries':['property_id','buyer_id'],'property_visits':['property_id','buyer_id'],'property_reports':['property_id']}.items():
        for column in columns: op.create_index('ix_'+table+'_'+column,table,[column])
def downgrade():
    raise RuntimeError('Property records require an explicit retention/export plan before downgrade')
