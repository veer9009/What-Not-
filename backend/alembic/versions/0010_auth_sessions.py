"""Hashed, rotating refresh session families. Prepare only; operator applies."""
from alembic import op
import sqlalchemy as sa

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('auth_sessions',
        sa.Column('id', sa.String(32), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id'), sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'))
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])
    op.create_index('ix_auth_sessions_expires_at', 'auth_sessions', ['expires_at'])
    op.create_table('auth_refresh_tokens',
        sa.Column('digest', sa.String(64), nullable=False),
        sa.Column('session_id', sa.String(32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('digest'),
        sa.ForeignKeyConstraint(['session_id'], ['auth_sessions.id'], ondelete='CASCADE'))
    op.create_index('ix_auth_refresh_tokens_session_id', 'auth_refresh_tokens', ['session_id'])


def downgrade():
    # This guard also appears in offline SQL. Never silently destroy revocation
    # or replay history; recovery must explicitly archive and remove sessions.
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM auth_sessions) THEN
            RAISE EXCEPTION 'Refusing downgrade with authentication session history; use reviewed recovery procedure';
        END IF;
    END $$""")
    op.drop_table('auth_refresh_tokens')
    op.drop_table('auth_sessions')
