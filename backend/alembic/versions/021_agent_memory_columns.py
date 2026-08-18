"""Add the agent_memories columns the AgentMemory model declares

The table was created without `role`, `metadata` and `updated_at`, all three of
which the model has. Since SQLAlchemy names every mapped column in its SELECT,
this made *reading* an agent's memory fail with UndefinedColumn, not just
writing one — agent chat and recall were unusable against a migrated database.

Revision ID: 021
Revises: 020
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'agent_memories',
        sa.Column(
            'role',
            sa.String(length=50),
            nullable=False,
            server_default='assistant',
        ),
    )
    op.add_column(
        'agent_memories',
        sa.Column(
            'metadata',
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            server_default='{}',
        ),
    )
    op.add_column(
        'agent_memories',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # TimestampMixin supplies this default; the table was created without one.
    op.alter_column(
        'agent_memories',
        'created_at',
        server_default=sa.func.now(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'agent_memories',
        'created_at',
        server_default=None,
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
    op.drop_column('agent_memories', 'updated_at')
    op.drop_column('agent_memories', 'metadata')
    op.drop_column('agent_memories', 'role')
