"""Installed vertical packs

Installation state lived in two module-level dicts that disagreed with each
other — one in the routes, one in services/verticals/installer.py — and both
emptied on restart. A workspace that had installed the Security pack reported
nothing installed after a deploy, while the pack's pipelines and alert presets
were still expected to be in place.

The installer's dict is intentionally left alone: it holds live VerticalPack
instances, which are objects rather than state. What persists here is the fact
of the install and its per-component toggles.

Revision ID: 013
Revises: 012
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'installed_vertical_packs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('pack_id', sa.String(length=64), nullable=False),
        sa.Column('installed_version', sa.String(length=32), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('enabled_modules', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('enabled_pipelines', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('enabled_alerts', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'pack_id', name='uq_installed_pack_workspace'),
    )
    op.create_index(
        'ix_installed_vertical_packs_workspace',
        'installed_vertical_packs',
        ['workspace_id'],
        unique=False,
    )

    op.create_table(
        'vertical_install_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('pack_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('steps', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_vertical_install_jobs_workspace',
        'vertical_install_jobs',
        ['workspace_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_vertical_install_jobs_workspace', table_name='vertical_install_jobs')
    op.drop_table('vertical_install_jobs')
    op.drop_index('ix_installed_vertical_packs_workspace', table_name='installed_vertical_packs')
    op.drop_table('installed_vertical_packs')
