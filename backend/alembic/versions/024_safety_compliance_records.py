"""Safety compliance records

Scan results, legal holds and voice consent were module-level dicts. All three
exist because someone may ask for them later, so losing them on restart turns
"was this scanned?" and "is this under hold?" silently into no. A legal hold
that evaporates does not just lose data — it lifts the block without anyone
releasing it.

Revision ID: 024
Revises: 023
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('voice_consents',
    sa.Column('voice_owner_id', sa.String(length=128), nullable=False),
    sa.Column('user_id', sa.String(length=128), nullable=False),
    sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('voice_owner_id', 'user_id', name='uq_voice_consent_pair')
    )
    op.create_index('ix_voice_consents_owner', 'voice_consents', ['voice_owner_id'], unique=False)
    op.create_table('legal_holds',
    sa.Column('workspace_id', sa.UUID(), nullable=True),
    sa.Column('asset_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('placed_by', sa.String(length=128), nullable=True),
    sa.Column('released', sa.Boolean(), nullable=False),
    sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('released_by', sa.String(length=128), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_legal_holds_released', 'legal_holds', ['released'], unique=False)
    op.create_index('ix_legal_holds_workspace', 'legal_holds', ['workspace_id'], unique=False)
    op.create_table('safety_scans',
    sa.Column('workspace_id', sa.UUID(), nullable=True),
    sa.Column('asset_id', sa.String(length=128), nullable=True),
    sa.Column('scan_type', sa.String(length=32), nullable=False),
    sa.Column('faces_detected', sa.Integer(), nullable=False),
    sa.Column('risk_score', sa.Float(), nullable=False),
    sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_safety_scans_asset', 'safety_scans', ['asset_id'], unique=False)
    op.create_index('ix_safety_scans_workspace', 'safety_scans', ['workspace_id'], unique=False)


def downgrade() -> None:
    op.drop_table('safety_scans')
    op.drop_table('legal_holds')
    op.drop_table('voice_consents')
