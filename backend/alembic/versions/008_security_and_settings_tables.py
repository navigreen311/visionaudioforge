"""Account security and settings persistence

Sessions, login history, two-factor enrolment, appearance preferences and
workspace integrations moved off module-level lists.

These were wrong in two ways at once, not one. They did not survive a restart,
and they were not scoped to anybody: a single module-level ``_2fa_enabled``
boolean reported one account's enrolment as every account's, one session list
showed every user the same devices, and appearance preferences were keyed by
the literal string "default" so one user's theme was everyone's.

Revision ID: 008
Revises: 007
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device', sa.String(length=200), nullable=False),
        sa.Column('browser', sa.String(length=200), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=False),
        sa.Column('last_active', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_sessions_user_active', 'user_sessions', ['user_id', 'last_active'], unique=False)

    op.create_table(
        'login_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('device', sa.String(length=200), nullable=False),
        sa.Column('browser', sa.String(length=200), nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('status', sa.Enum('success', 'failed', name='loginstatus'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_login_events_user_timestamp', 'login_events', ['user_id', 'timestamp'], unique=False)

    op.create_table(
        'user_two_factor',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('secret', sa.String(length=64), nullable=True),
        sa.Column('enabled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    op.create_table(
        'appearance_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('preferences', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    op.create_table(
        'workspace_integrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('connected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workspace_integrations_workspace', 'workspace_integrations', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_workspace_integrations_workspace', table_name='workspace_integrations')
    op.drop_table('workspace_integrations')
    op.drop_table('appearance_preferences')
    op.drop_table('user_two_factor')
    op.drop_index('ix_login_events_user_timestamp', table_name='login_events')
    op.drop_table('login_events')
    op.drop_index('ix_user_sessions_user_active', table_name='user_sessions')
    op.drop_table('user_sessions')
    sa.Enum(name='loginstatus').drop(op.get_bind(), checkfirst=True)
