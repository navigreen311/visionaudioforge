"""Bring experiments in line with the Experiment model

Three separate mismatches between `experiments` and the model:

* `error_message` is declared on the model but the table never had it, so any
  query naming it failed with UndefinedColumn — which is every read of an
  experiment through the ORM.
* `best_epoch` is `Integer` on the model and `json` in the table.
* The `experimentstatus` enum lacks `cancelled`, which `POST
  /experiments/{id}/cancel` writes, so cancelling an experiment could not work.

Revision ID: 020
Revises: 019
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'experiments',
        sa.Column('error_message', sa.String(length=1000), nullable=True),
    )

    op.alter_column(
        'experiments',
        'best_epoch',
        type_=sa.Integer(),
        existing_type=sa.JSON(),
        postgresql_using='NULLIF(best_epoch::text, \'null\')::integer',
        existing_nullable=True,
    )

    op.alter_column(
        'experiments',
        'name',
        type_=sa.String(length=255),
        existing_type=sa.String(length=200),
        existing_nullable=False,
    )

    # Safe inside a transaction on PostgreSQL 12+ as long as the new label is
    # not also *used* in this migration.
    op.execute("ALTER TYPE experimentstatus ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # A label cannot be removed from a PostgreSQL enum; 'cancelled' stays.
    op.alter_column(
        'experiments',
        'name',
        type_=sa.String(length=200),
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )

    op.alter_column(
        'experiments',
        'best_epoch',
        type_=sa.JSON(),
        existing_type=sa.Integer(),
        postgresql_using='to_json(best_epoch)',
        existing_nullable=True,
    )

    op.drop_column('experiments', 'error_message')
