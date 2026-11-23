"""Add encrypted recovery delivery only. Operators apply separately."""
from alembic import op
import sqlalchemy as sa

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('recovery_deliveries',
        sa.Column('challenge', sa.String(43), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('ciphertext', sa.LargeBinary()),
        sa.Column('key_id', sa.String(32)),
        sa.Column('state', sa.String(16), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('lease_until', sa.DateTime(timezone=True)),
        sa.Column('lease_token', sa.String(36)),
        sa.Column('last_error_code', sa.String(40)),
        sa.PrimaryKeyConstraint('challenge'),
        sa.ForeignKeyConstraint(['challenge'], ['password_recoveries.challenge'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.CheckConstraint("state IN ('PENDING','LEASED','SENT','FAILED','CANCELLED')", name=op.f('ck_recovery_deliveries_state')),
        sa.CheckConstraint('attempts >= 0', name=op.f('ck_recovery_deliveries_attempts')),
        sa.CheckConstraint("(state='LEASED' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) OR "
                           "(state<>'LEASED' AND lease_token IS NULL AND lease_until IS NULL)",
                           name=op.f('ck_recovery_deliveries_lease')),
        sa.CheckConstraint("(state IN ('SENT','FAILED','CANCELLED') AND ciphertext IS NULL AND key_id IS NULL) OR "
                           "(state IN ('PENDING','LEASED') AND ciphertext IS NOT NULL AND key_id IS NOT NULL)",
                           name=op.f('ck_recovery_deliveries_payload')))
    for column in ('user_id', 'expires_at', 'next_attempt_at', 'lease_until'):
        op.create_index('ix_recovery_deliveries_' + column, 'recovery_deliveries', [column])


def downgrade():
    op.execute('LOCK TABLE recovery_deliveries IN ACCESS EXCLUSIVE MODE')
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM recovery_deliveries) THEN
            RAISE EXCEPTION 'Refusing downgrade with recovery delivery history';
        END IF;
    END $$""")
    op.drop_table('recovery_deliveries')
