"""Create the nil-UUID system workspace the code falls back to

Thirteen call sites across agents, search, annotation and saved searches use
`00000000-0000-0000-0000-000000000000` as the workspace for rows that arrive
without one. The row was never created, so every one of those writes failed on
`workspaces` foreign keys — agent chat, for one, could not record a message.

Creating it makes the existing fallback resolve. It is a holding area for
unattributed rows, not a tenant: nothing should be granted access to it.

Revision ID: 021
Revises: 020
Create Date: 2026-08-17
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '021'
down_revision = '020'
branch_labels = None
depends_on = None

SYSTEM_WORKSPACE_ID = '00000000-0000-0000-0000-000000000000'


def upgrade() -> None:
    op.execute(
        f"""
        INSERT INTO workspaces (id, name, slug, plan, settings)
        VALUES (
            '{SYSTEM_WORKSPACE_ID}',
            'System',
            'system',
            'free',
            '{{"system": true, "description": "Holds rows written without a workspace."}}'
        )
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    # Only remove it if nothing was filed against it.
    op.execute(
        f"""
        DELETE FROM workspaces w
        WHERE w.id = '{SYSTEM_WORKSPACE_ID}'
          AND NOT EXISTS (SELECT 1 FROM events e WHERE e.workspace_id = w.id)
        """
    )
