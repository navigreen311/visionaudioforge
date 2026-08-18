"""Agent conversations

Conversation history was a module-level dict pre-seeded with three invented
threads, so a fresh install showed transcripts of troubleshooting sessions
nobody had run — and anything a user actually said was lost on restart.

Revision ID: 012
Revises: 011
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'agent_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('agent_id', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_conversations_workspace', 'agent_conversations', ['workspace_id'], unique=False)

    op.create_table(
        'agent_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['agent_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_agent_messages_conversation_timestamp',
        'agent_messages',
        ['conversation_id', 'timestamp'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_agent_messages_conversation_timestamp', table_name='agent_messages')
    op.drop_table('agent_messages')
    op.drop_index('ix_agent_conversations_workspace', table_name='agent_conversations')
    op.drop_table('agent_conversations')
