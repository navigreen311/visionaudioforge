"""Federated learning persistence

The coordinator held federations in a module-level dict and recorded no round
at all, so /rounds had nothing to return and the console's training chart was
filled from a generator instead of a run. A federation is a collaboration that
runs for days across organisations; losing it on restart, or losing which
sites contributed to which round, loses the experiment.

Scope note: --autogenerate also reports column drift between earlier
migrations and the current models on model_registry, agents, experiments and
edge_devices. Reconciling that means retyping columns on populated tables and
belongs with whoever owns them, so this migration is purely additive.

Revision ID: 023
Revises: 022
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('federations',
    sa.Column('workspace_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('model_id', sa.String(length=200), nullable=False),
    sa.Column('status', sa.Enum('waiting', 'ready', 'training', 'paused', 'completed', 'stopped', name='federationstatus'), nullable=False),
    sa.Column('aggregation_strategy', sa.String(length=32), nullable=False),
    sa.Column('min_participants', sa.Integer(), nullable=False),
    sa.Column('total_rounds', sa.Integer(), nullable=False),
    sa.Column('current_round', sa.Integer(), nullable=False),
    sa.Column('privacy_budget', sa.Float(), nullable=False),
    sa.Column('privacy_epsilon_spent', sa.Float(), nullable=False),
    sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('global_model', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_federations_workspace', 'federations', ['workspace_id'], unique=False)
    op.create_table('federation_participants',
    sa.Column('federation_id', sa.UUID(), nullable=False),
    sa.Column('site', sa.String(length=200), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('data_size', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('connected', 'disconnected', 'reconnecting', 'removed', name='participantstatus'), nullable=False),
    sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('rounds_contributed', sa.Integer(), nullable=False),
    sa.Column('samples_contributed', sa.Integer(), nullable=False),
    sa.Column('info', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['federation_id'], ['federations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('federation_id', 'site', name='uq_federation_participant_site')
    )
    op.create_index('ix_federation_participants_federation', 'federation_participants', ['federation_id'], unique=False)
    op.create_table('federation_rounds',
    sa.Column('federation_id', sa.UUID(), nullable=False),
    sa.Column('round_number', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('in_progress', 'completed', 'failed', name='roundstatus'), nullable=False),
    sa.Column('global_model_version', sa.String(length=64), nullable=False),
    sa.Column('participant_count', sa.Integer(), nullable=False),
    sa.Column('updates_received', sa.Integer(), nullable=False),
    sa.Column('updates', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('aggregated_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('privacy_epsilon_spent', sa.Float(), nullable=False),
    sa.Column('aggregation_time_ms', sa.Float(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['federation_id'], ['federations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('federation_id', 'round_number', name='uq_federation_round_number')
    )
    op.create_index('ix_federation_rounds_federation', 'federation_rounds', ['federation_id'], unique=False)


def downgrade() -> None:
    op.drop_table('federation_rounds')
    op.drop_table('federation_participants')
    op.drop_table('federations')
