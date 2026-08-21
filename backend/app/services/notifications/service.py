"""Writing and reading notifications.

`emit` is the only way a notification is created. It fans out to the workspace's
users, because read state is per person - see app/models/notification.py.

Every producer calls it the same way and none of them may fail because of it: a
notification is a side effect of something that already happened, so a broken
bell must not roll back an alert that fired or a training run that finished.
`emit` therefore swallows and logs its own failures. That is the one place in
this codebase where a bare catch is the right answer, and it is confined here
rather than left to each caller.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Notifications for a workspace's users."""

    @staticmethod
    async def emit(
        db: AsyncSession,
        workspace_id: UUID,
        type_: NotificationType,
        title: str,
        description: str = "",
        action_url: str | None = None,
    ) -> int:
        """Notify every user in *workspace_id*. Returns how many rows were written.

        Never raises. A producer calls this after the thing it describes has
        already been committed, so an exception here would fail an operation
        that succeeded.
        """
        try:
            recipients = (
                await db.execute(
                    select(User.id).where(User.workspace_id == workspace_id)
                )
            ).scalars().all()

            if not recipients:
                # A workspace with no users is not an error - a system workspace
                # or a fixture can be in that state - and there is nobody to tell.
                return 0

            db.add_all(
                [
                    Notification(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        type=type_,
                        title=title[:200],
                        description=description,
                        action_url=action_url,
                    )
                    for user_id in recipients
                ]
            )
            await db.commit()
            return len(recipients)

        except Exception:  # noqa: BLE001 - see the module docstring
            logger.exception(
                "could not write notification %r for workspace %s", title, workspace_id
            )
            try:
                await db.rollback()
            except Exception:  # noqa: BLE001
                logger.exception("rollback after a failed notification also failed")
            return 0

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    @staticmethod
    async def list_for_user(
        db: AsyncSession, user_id: UUID, limit: int = 50
    ) -> list[dict[str, Any]]:
        """This user's notifications, newest first."""
        rows = (
            await db.execute(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()

        return [NotificationService.serialise(row) for row in rows]

    @staticmethod
    async def unread_count(db: AsyncSession, user_id: UUID) -> int:
        """How many of this user's notifications are unread."""
        return (
            await db.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
        ).scalar() or 0

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    @staticmethod
    async def mark_read(
        db: AsyncSession, user_id: UUID, notification_id: UUID
    ) -> bool:
        """Mark one notification read. False if it is not this user's.

        The `user_id` in the WHERE clause is the point: without it, an id from
        another tenant would be marked read by whoever guessed it.
        """
        result = await db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return bool(result.rowcount)

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: UUID) -> int:
        """Mark every unread notification of this user's read."""
        result = await db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return result.rowcount or 0

    # ------------------------------------------------------------------
    # Shape
    # ------------------------------------------------------------------

    @staticmethod
    def serialise(row: Notification) -> dict[str, Any]:
        """The shape the console's NotificationCenter reads.

        `read` stays a boolean in the payload even though the column is a
        timestamp: the console types it as one, and the exact moment something
        was seen is not the bell's business.
        """
        return {
            "id": str(row.id),
            "type": row.type.value if hasattr(row.type, "value") else str(row.type),
            "title": row.title,
            "description": row.description or "",
            "read": row.read_at is not None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "action_url": row.action_url or "",
        }
