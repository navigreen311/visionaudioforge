"""Add pipelines.description

PipelineCreate accepted a description and PipelineRead promised one on every
read, but the Pipeline model declared no such column. Both persistence routes
passed it to the constructor anyway:

    TypeError: 'description' is an invalid keyword argument for Pipeline

so POST /api/pipeline/create and POST /api/pipeline/save each answered 500 and
no pipeline could be saved — not from the builder, not from an API client.

Adding the column rather than removing the argument, because two of the three
schema surfaces already require it: the request accepts it and, more
importantly, the *response* model declares it, so the published contract says a
pipeline has a description. Dropping it would mean a breaking change to both
schemas to retract a promise; adding a nullable column makes the promise true
and breaks nothing. Nullable because the console's save sends only name and
definition.

Revision ID: 026
Revises: 025
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('pipelines', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('pipelines', 'description')
