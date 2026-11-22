"""Add digest-only password recovery. Operator applies separately."""
from alembic import op
import sqlalchemy as sa

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('password_recoveries',
        sa.Column('challenge', sa.String(43), nullable=False),
        sa.Column('user_id', sa.BigInteger()),
        sa.Column('email_digest', sa.String(64), nullable=False),
        sa.Column('otp_digest', sa.String(64), nullable=False),
        sa.Column('password_binding', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('reset_digest', sa.String(64)),
        sa.Column('reset_expires_at', sa.DateTime(timezone=True)),
        sa.Column('used_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('challenge'), sa.UniqueConstraint('reset_digest'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'))
    for column in ('user_id', 'email_digest', 'expires_at'):
        op.create_index('ix_password_recoveries_' + column, 'password_recoveries', [column])


def downgrade():
    # Hold through the check and DROP in Alembic's PostgreSQL transaction.
    # Otherwise concurrent issuance can insert history after the empty check.
    op.execute('LOCK TABLE password_recoveries IN ACCESS EXCLUSIVE MODE')
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM password_recoveries) THEN
            RAISE EXCEPTION 'Refusing downgrade with recovery credential history';
        END IF;
    END $$""")
    op.drop_table('password_recoveries')
