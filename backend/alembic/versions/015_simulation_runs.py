"""Simulation scenarios and runs

A simulation run is a result someone waited for: replay, comparison and the
report all read it back by id. Held in module-level dicts, every one of those
raised "Simulation not found" after a restart even though the run had completed
successfully — and saved scenarios disappeared with them.

The run stores the scenario as it was at run time rather than referencing it,
so replaying an old run reproduces what it actually ran, not whatever the
scenario has since been edited into.

Revision ID: 015
Revises: 014
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'simulation_scenarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('scenario_type', sa.String(length=64), nullable=False),
        sa.Column('definition', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_simulation_scenarios_workspace', 'simulation_scenarios', ['workspace_id'], unique=False)

    op.create_table(
        'simulation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scenario', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('events_injected', sa.Integer(), nullable=False),
        sa.Column('alerts_triggered', sa.Integer(), nullable=False),
        sa.Column('duration_s', sa.Float(), nullable=False),
        sa.Column('timeline', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('label', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_simulation_runs_workspace', 'simulation_runs', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_simulation_runs_workspace', table_name='simulation_runs')
    op.drop_table('simulation_runs')
    op.drop_index('ix_simulation_scenarios_workspace', table_name='simulation_scenarios')
    op.drop_table('simulation_scenarios')
