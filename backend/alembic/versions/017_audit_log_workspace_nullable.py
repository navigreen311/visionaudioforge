"""Allow audit_logs.workspace_id to be NULL

An audit trail whose every row must name a tenant cannot record the events that
happen before a tenant is known. The most important of those is a failed login:
the single event an auditor asks for first, and the one this table could not
hold.

The NOT NULL constraint had two visible consequences. The request-audit
middleware skipped every unauthenticated request outright, because the insert
would have failed. And app/services/alerts/chain_of_custody.py guards its write
with `if workspace is not None`, dropping custody events it could not attribute
rather than storing them unattributed.

Dropping NOT NULL is safe in both directions for existing data: every row
written so far necessarily has a workspace, so the downgrade below can restore
the constraint as long as no unattributed rows have been written since. It
deletes them first rather than failing halfway — an audit row with no tenant is
exactly what this revision introduced, so removing them is undoing this change,
not discarding unrelated data.

Revision ID: 017
Revises: 016
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'audit_logs',
        'workspace_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # Rows created while the column was nullable have no tenant and cannot be
    # given one. They are the artefact of this revision, so undoing it removes
    # them; without this the ALTER would fail against its own data.
    op.execute(sa.text("DELETE FROM audit_logs WHERE workspace_id IS NULL"))
    op.alter_column(
        'audit_logs',
        'workspace_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
