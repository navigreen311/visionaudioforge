"""Field notes

A note written in the field is the one piece of data on that device that exists
nowhere else — it is typed by an operator standing in front of something. Held
in a module-level dict it was lost on the next deploy, silently.

Push registrations move onto the existing push_devices table and developer node
templates onto custom_nodes, so neither needs a table of its own.

Revision ID: 014
Revises: 013
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'field_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('location', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('attachments', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_field_notes_workspace', 'field_notes', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_field_notes_workspace', table_name='field_notes')
    op.drop_table('field_notes')
