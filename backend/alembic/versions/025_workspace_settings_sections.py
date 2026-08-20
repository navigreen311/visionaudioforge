"""Workspace settings sections

General, security and notification settings were three module-level dicts
seeded from their Pydantic defaults, so every save was forgotten on restart
and the console redisplayed the defaults as though nothing had been
configured. One row per (workspace, section), stored as a document so adding
a control does not need a migration.

Revision ID: 025
Revises: 024
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('workspace_settings',
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('section', sa.String(length=64), nullable=False),
    sa.Column('value', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('workspace_id', 'section', name='uq_workspace_setting_section')
    )
    op.create_index('ix_workspace_settings_workspace', 'workspace_settings', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('workspace_settings')
