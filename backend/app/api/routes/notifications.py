"""Notification routes.

These served five hardcoded entries from a module-level list to every user of
every workspace, and mark-as-read mutated that shared list - so one person's
click cleared the badge for every tenant on the deployment, and a restart
brought all five back unread. See app/models/notification.py for why a
notification is now one row per recipient.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.notifications.service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """This user's notifications, newest first."""
    return await NotificationService.list_for_user(db, current_user.id, limit=limit)


@router.get("/unread-count")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """The number on the bell. Polled every 30 seconds by the console."""
    return {"count": await NotificationService.unread_count(db, current_user.id)}


@router.patch("/{notif_id}/read")
async def mark_read(
    notif_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark one notification read.

    404 rather than `{"success": false}`: the previous handler answered 200 with
    a false flag for an id it could not find, which the console did not check,
    so a failed write looked like a successful one.
    """
    if not await NotificationService.mark_read(db, current_user.id, notif_id):
        raise HTTPException(
            status_code=404, detail="No unread notification with that id for this user"
        )
    return {"success": True}


@router.post("/read-all")
async def read_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark every unread notification of this user's read."""
    return {
        "success": True,
        "marked": await NotificationService.mark_all_read(db, current_user.id),
    }
