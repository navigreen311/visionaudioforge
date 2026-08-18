"""Pipeline schedules and inference cost control

Both subsystems kept their state per process instance, which made each one
quietly wrong in a way nothing reported.

The scheduler wrote to the pipeline's definition JSON but read from memory, so
after a restart it listed no schedules while the rows still existed — a
scheduler that stops scheduling and shows nothing to explain why.

Quotas were worse: a cap that resets on deploy is not a cap, and because each
worker counted its own usage a four-worker deployment allowed roughly four
times the configured limit. check_quota now takes a row lock so two workers
cannot both consume the last remaining unit.

Revision ID: 009
Revises: 008
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pipeline_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cron', sa.String(length=120), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('next_run', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pipeline_schedules_workspace', 'pipeline_schedules', ['workspace_id'], unique=False)
    op.create_index('ix_pipeline_schedules_pipeline', 'pipeline_schedules', ['pipeline_id'], unique=False)

    op.create_table(
        'inference_cost_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model_id', sa.String(length=200), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.Column('tokens_or_pixels', sa.Integer(), nullable=False),
        sa.Column('cost', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_inference_cost_events_workspace_timestamp',
        'inference_cost_events',
        ['workspace_id', 'timestamp'],
        unique=False,
    )

    op.create_table(
        'workspace_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('daily_limit', sa.Integer(), nullable=False),
        sa.Column('used', sa.Integer(), nullable=False),
        sa.Column('resets_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id'),
    )

    op.create_table(
        'model_cost_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_id', sa.String(length=200), nullable=False),
        sa.Column('cost_per_unit', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_id'),
    )


def downgrade() -> None:
    op.drop_table('model_cost_rates')
    op.drop_table('workspace_quotas')
    op.drop_index('ix_inference_cost_events_workspace_timestamp', table_name='inference_cost_events')
    op.drop_table('inference_cost_events')
    op.drop_index('ix_pipeline_schedules_pipeline', table_name='pipeline_schedules')
    op.drop_index('ix_pipeline_schedules_workspace', table_name='pipeline_schedules')
    op.drop_table('pipeline_schedules')
