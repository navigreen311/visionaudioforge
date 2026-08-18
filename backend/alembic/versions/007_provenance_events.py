"""Asset provenance events

Moves the provenance chain off a module-level dict.

Provenance is an integrity claim about an asset's history. Held in memory it
reports a complete chain right up until the process restarts, at which point it
silently becomes "no events recorded" — which reads identically to an asset
nothing ever touched. Rows are append-only; there is no update path, because
rewriting provenance defeats its purpose.

Revision ID: 007
Revises: 006
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'provenance_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asset_id', sa.String(length=64), nullable=False),
        sa.Column(
            'action',
            sa.Enum(
                'created',
                'transformed',
                'exported',
                'shared',
                'ai_generated',
                'annotated',
                name='provenanceaction',
            ),
            nullable=False,
        ),
        # Text rather than a users FK so the chain still names who acted after
        # an account is deleted.
        sa.Column('user_id', sa.String(length=200), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column(
            'timestamp',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_provenance_events_asset_timestamp',
        'provenance_events',
        ['asset_id', 'timestamp'],
        unique=False,
    )
    op.create_index(
        'ix_provenance_events_workspace',
        'provenance_events',
        ['workspace_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_provenance_events_workspace', table_name='provenance_events')
    op.drop_index(
        'ix_provenance_events_asset_timestamp', table_name='provenance_events'
    )
    op.drop_table('provenance_events')
    sa.Enum(name='provenanceaction').drop(op.get_bind(), checkfirst=True)
