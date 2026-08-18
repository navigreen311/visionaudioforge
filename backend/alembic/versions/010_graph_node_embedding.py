"""Add graph_nodes.embedding

GraphService.create_node has always accepted an ``embedding`` argument, but no
such column existed: it was declared only on a second, unregistered GraphNode
in app/models/knowledge_graph.py. That module also redefined graph_nodes and
graph_edges with different column names (edge_type/confidence rather than the
relation/weight the database actually has), so importing it alongside the real
models raised "Table 'graph_nodes' is already defined" and made every
services/knowledge_graph module unimportable. The duplicate is gone; this adds
the one column it contributed that the service genuinely uses.

Revision ID: 010
Revises: 009
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'graph_nodes',
        sa.Column('embedding', sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('graph_nodes', 'embedding')
