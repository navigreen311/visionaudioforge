"""Add the notifications table

/api/notifications served five hardcoded entries from a module-level list to
every user of every workspace. Marking one read mutated that shared list, so one
person's click cleared the badge for every tenant on the deployment, and a
restart brought all five back unread. There was nowhere to read a real
notification from, because there was no table.

One row per recipient rather than one row per event with a join table: read
state is per person, so a bell that says "3 unread" means three things that user
has not seen. That makes read_at a plain column and the bell's hot query — this
user's unread count — a single indexed count.

Revision ID: 027
Revises: 026
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'workspace_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('workspaces.id'),
            nullable=False,
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'type',
            sa.Enum('alert', 'pipeline', 'model', 'system', name='notificationtype'),
            nullable=False,
        ),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('action_url', sa.String(length=500), nullable=True),
        # Null means unread.
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # The bell's two queries: this user's list newest-first, and their unread
    # count.
    op.create_index(
        'ix_notifications_user_created', 'notifications', ['user_id', 'created_at']
    )
    op.create_index(
        'ix_notifications_user_unread', 'notifications', ['user_id', 'read_at']
    )
    op.create_index('ix_notifications_workspace', 'notifications', ['workspace_id'])


def downgrade() -> None:
    op.drop_index('ix_notifications_workspace', table_name='notifications')
    op.drop_index('ix_notifications_user_unread', table_name='notifications')
    op.drop_index('ix_notifications_user_created', table_name='notifications')
    op.drop_table('notifications')
    sa.Enum(name='notificationtype').drop(op.get_bind(), checkfirst=True)
