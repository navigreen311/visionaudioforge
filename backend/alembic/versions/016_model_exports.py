"""Model exports and edge benchmarks

An export job produces an artefact and a download URL that a user comes back
for later. Held in a module-level dict, the artefact outlived the record of it:
after a restart the job reported "not found" while the exported file was still
sitting in storage with nothing pointing at it.

Built packages already have a home in offline_packages, so only exports and
benchmarks need tables.

Revision ID: 016
Revises: 015
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'model_exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model_id', sa.String(length=200), nullable=False),
        sa.Column('format', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('optimize', sa.Boolean(), nullable=False),
        sa.Column('quantize', sa.Boolean(), nullable=False),
        sa.Column('file_size_mb', sa.Float(), nullable=True),
        sa.Column('download_url', sa.String(length=1000), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_model_exports_workspace', 'model_exports', ['workspace_id'], unique=False)
    op.create_index('ix_model_exports_model', 'model_exports', ['model_id'], unique=False)

    op.create_table(
        'edge_benchmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model_id', sa.String(length=200), nullable=False),
        sa.Column('device_type', sa.String(length=50), nullable=False),
        sa.Column('results', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_edge_benchmarks_workspace', 'edge_benchmarks', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_edge_benchmarks_workspace', table_name='edge_benchmarks')
    op.drop_table('edge_benchmarks')
    op.drop_index('ix_model_exports_model', table_name='model_exports')
    op.drop_index('ix_model_exports_workspace', table_name='model_exports')
    op.drop_table('model_exports')
