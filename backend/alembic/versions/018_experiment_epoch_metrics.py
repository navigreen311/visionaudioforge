"""Bring experiment_epochs in line with the ExperimentEpoch model

The table was created with (epoch, metrics, timestamp) while the model declares
epoch_number, train_loss, val_loss, accuracy, val_accuracy, metrics, plus the
created_at/updated_at of TimestampMixin. Logging an epoch therefore failed
against every migrated database, and the route turned the resulting error into
a bare 404 "Experiment not found", which hid the cause.

Renames rather than drops, so existing epoch history survives.

Revision ID: 018
Revises: 017
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('experiment_epochs', 'epoch', new_column_name='epoch_number')
    op.alter_column('experiment_epochs', 'timestamp', new_column_name='created_at')

    for column in ('train_loss', 'val_loss', 'accuracy', 'val_accuracy'):
        op.add_column('experiment_epochs', sa.Column(column, sa.Float(), nullable=True))

    op.add_column(
        'experiment_epochs',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # `metrics` is nullable on the model; the table declared it NOT NULL.
    op.alter_column('experiment_epochs', 'metrics', nullable=True)


def downgrade() -> None:
    op.alter_column('experiment_epochs', 'metrics', nullable=False)
    op.drop_column('experiment_epochs', 'updated_at')

    for column in ('val_accuracy', 'accuracy', 'val_loss', 'train_loss'):
        op.drop_column('experiment_epochs', column)

    op.alter_column('experiment_epochs', 'created_at', new_column_name='timestamp')
    op.alter_column('experiment_epochs', 'epoch_number', new_column_name='epoch')
