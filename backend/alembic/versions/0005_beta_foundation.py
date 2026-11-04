"""Durable beta delivery lifecycle, audit and recipient outbox foundation."""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('audit_events',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('actor_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT')),
        sa.Column('actor_type', sa.String(32), nullable=False),
        sa.Column('entity_type', sa.String(40), nullable=False),
        sa.Column('entity_id', sa.BigInteger(), nullable=False),
        sa.Column('action', sa.String(80), nullable=False),
        sa.Column('previous_status', sa.String(40)), sa.Column('next_status', sa.String(40)),
        sa.Column('reason', sa.String(1200)))
    for column in ('entity_type', 'entity_id'):
        op.create_index(f'ix_audit_events_{column}', 'audit_events', [column])
    op.create_table('notifications',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('recipient_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('event_key', sa.String(200), nullable=False), sa.Column('kind', sa.String(80), nullable=False),
        sa.Column('entity_type', sa.String(40), nullable=False), sa.Column('entity_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False), sa.Column('body', sa.String(1000), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True)),
        sa.UniqueConstraint('event_key', 'recipient_id', name='uq_notifications_event_recipient'))
    op.create_index('ix_notifications_recipient_id', 'notifications', ['recipient_id'])
    op.create_table('email_outbox',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('recipient_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('event_key', sa.String(200), nullable=False), sa.Column('kind', sa.String(80), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('state', sa.String(16), nullable=False, server_default='PENDING'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('lease_until', sa.DateTime(timezone=True)), sa.Column('lease_token', sa.String(36)),
        sa.Column('last_error_code', sa.String(80)), sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('provider_reference', sa.String(200)),
        sa.UniqueConstraint('event_key', 'recipient_id', name='uq_email_outbox_event_recipient'),
        sa.CheckConstraint("state IN ('PENDING','LEASED','SENT','FAILED')", name=op.f('ck_email_outbox_state')),
        sa.CheckConstraint('attempts >= 0', name=op.f('ck_email_outbox_attempts')))
    for column in ('recipient_id', 'next_attempt_at'):
        op.create_index(f'ix_email_outbox_{column}', 'email_outbox', [column])
    for name in ('delivered_at', 'confirmation_deadline', 'completed_at'):
        op.add_column('orders', sa.Column(name, sa.DateTime(timezone=True)))
    op.add_column('orders', sa.Column('completion_source', sa.String(32)))
    op.create_index('ix_orders_confirmation_deadline', 'orders', ['confirmation_deadline'])
    op.drop_constraint(op.f('ck_orders_status'), 'orders', type_='check')
    # 24 hours is the frozen migration rollout policy, not runtime configuration.
    op.execute("""INSERT INTO audit_events(actor_type,entity_type,entity_id,action,previous_status,next_status,reason)
        SELECT 'MIGRATION','order',id,'ORDER_MIGRATION',status,
        CASE WHEN status='DELIVERED' THEN 'COMPLETED' ELSE 'DELIVERED' END,
        '0005_LEGACY_MAPPING' FROM orders WHERE status IN ('DELIVERED','AWAITING_BUYER_CONFIRMATION')""")
    op.execute("UPDATE orders SET status='COMPLETED', completion_source='LEGACY' WHERE status='DELIVERED'")
    op.execute("UPDATE orders SET status='DELIVERED', confirmation_deadline=now()+interval '24 hours', completion_source='MIGRATION' WHERE status='AWAITING_BUYER_CONFIRMATION'")
    op.create_check_constraint(op.f('ck_orders_status'), 'orders', "status IN ('PLACED','ACCEPTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED','COMPLETED','DELIVERY_DISPUTED','CANCELLED','REJECTED')")


def downgrade():
    connection = op.get_bind()
    connection.execute(sa.text('LOCK TABLE orders, audit_events, notifications, email_outbox IN ACCESS EXCLUSIVE MODE'))
    if connection.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM audit_events) OR EXISTS(SELECT 1 FROM notifications) OR EXISTS(SELECT 1 FROM email_outbox) OR EXISTS(SELECT 1 FROM orders WHERE status IN ('COMPLETED','DELIVERY_DISPUTED') OR delivered_at IS NOT NULL OR confirmation_deadline IS NOT NULL OR completed_at IS NOT NULL OR completion_source IS NOT NULL)")):
        raise RuntimeError('Cannot downgrade beta lifecycle or durable events without data loss')
    op.drop_constraint(op.f('ck_orders_status'), 'orders', type_='check')
    op.create_check_constraint(op.f('ck_orders_status'), 'orders', "status IN ('PLACED','ACCEPTED','PREPARING','OUT_FOR_DELIVERY','AWAITING_BUYER_CONFIRMATION','DELIVERED','CANCELLED','REJECTED')")
    op.drop_index('ix_orders_confirmation_deadline', table_name='orders')
    for name in ('delivered_at', 'confirmation_deadline', 'completed_at', 'completion_source'):
        op.drop_column('orders', name)
    for table in ('email_outbox', 'notifications', 'audit_events'):
        op.drop_table(table)
