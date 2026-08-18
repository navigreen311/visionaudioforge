"""ReviewOps task queue

The /api/reviewops routes kept their tasks in a module-level dict while a
richer review_tasks table sat unused beside them. This adapts that table to the
endpoints' actual contract rather than adding a second, competing one:

- title/description: the queue is described by a task name, not only an asset
- asset_id becomes nullable: a task can cover a batch, or no asset at all,
  and requiring one is why the route never adopted this table
- assigned_to_label: reviewers are addressed by opaque ids that are not
  necessarily user rows, and an assignment must still name who holds the task
  after a user is deleted

Revision ID: 011
Revises: 010
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('review_tasks', sa.Column('title', sa.String(length=300), nullable=True))
    op.add_column('review_tasks', sa.Column('description', sa.Text(), nullable=True))
    op.add_column(
        'review_tasks',
        sa.Column('assigned_to_label', sa.String(length=200), nullable=True),
    )
    op.add_column(
        'review_tasks',
        sa.Column('asset_ids', sa.JSON(), nullable=True),
    )
    op.alter_column('review_tasks', 'asset_id', existing_type=sa.UUID(), nullable=True)
    op.alter_column(
        'review_tasks',
        'sla_deadline',
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'review_tasks',
        'sla_deadline',
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.alter_column('review_tasks', 'asset_id', existing_type=sa.UUID(), nullable=False)
    op.drop_column('review_tasks', 'asset_ids')
    op.drop_column('review_tasks', 'assigned_to_label')
    op.drop_column('review_tasks', 'description')
    op.drop_column('review_tasks', 'title')
