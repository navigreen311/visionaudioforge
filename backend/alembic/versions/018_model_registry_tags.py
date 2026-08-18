"""Add model_registry.tags and description

ModelRecord has declared both columns all along, but no migration ever created
them, so every insert through the ORM failed with UndefinedColumn — registering
a model was impossible against a migrated database.

Revision ID: 018
Revises: 017
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'model_registry',
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.add_column(
        'model_registry',
        sa.Column('description', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('model_registry', 'description')
    op.drop_column('model_registry', 'tags')
