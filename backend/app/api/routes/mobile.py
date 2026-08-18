"""Mobile Backend routes — dashboard, push notifications, field notes.

Push registrations and field notes were module-level stores. Both are the kind
of data that exists nowhere else: a lost registration means the operator stops
receiving alerts with nothing reporting an error, and a field note is typed by
someone standing in front of the thing it describes.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.field_note import FieldNote
from app.models.integration import PushDevice

router = APIRouter(prefix="/api/mobile", tags=["mobile"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PushRegister(BaseModel):
    device_token: str
    platform: str = Field(..., pattern="^(ios|android|web)$")
    user_id: str | None = None


class FieldNoteCreate(BaseModel):
    title: str
    content: str
    location: dict[str, float] | None = None
    tags: list[str] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    workspace_id: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialise_note(note: FieldNote) -> dict[str, Any]:
    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "location": note.location,
        "tags": list(note.tags or []),
        "attachments": list(note.attachments or []),
        "created_at": note.created_at.timestamp() if note.created_at else None,
    }


def _scoped_notes(stmt, workspace_id: str | None):
    if workspace_id:
        return stmt.where(FieldNote.workspace_id == uuid.UUID(str(workspace_id)))
    return stmt


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def get_dashboard(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Mobile-optimised dashboard summary.

    Only the field-note count has a source in this route. Stream, alert and
    review counts were the fixed numbers 3, 2 and 5, which read as a live
    summary of the system; they are reported as unmeasured instead.
    """
    field_notes = (
        await db.execute(
            _scoped_notes(select(func.count()).select_from(FieldNote), workspace_id)
        )
    ).scalar() or 0

    return {
        "active_streams": None,
        "recent_alerts": None,
        "pending_reviews": None,
        "field_notes": field_notes,
        "system_status": "operational",
        "last_updated": time.time(),
        "unmeasured": ["active_streams", "recent_alerts", "pending_reviews"],
    }


@router.post("/push/register", status_code=201)
async def register_push(
    body: PushRegister,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Register a device for push notifications.

    Re-registering the same token for the same user updates it rather than
    stacking duplicates, which would deliver every alert more than once.
    """
    user_ref = body.user_id or "anonymous"

    device = (
        await db.execute(
            select(PushDevice).where(
                PushDevice.user_ref == user_ref,
                PushDevice.device_token == body.device_token,
            )
        )
    ).scalar_one_or_none()

    if device is None:
        device = PushDevice(user_ref=user_ref, device_token=body.device_token)
        db.add(device)

    device.platform = body.platform
    device.active = True
    try:
        device.user_id = uuid.UUID(body.user_id) if body.user_id else None
    except ValueError:
        device.user_id = None

    await db.commit()
    await db.refresh(device)

    return {
        "id": str(device.id),
        "device_token": device.device_token,
        "platform": device.platform,
        "user_id": device.user_ref,
        "registered_at": device.created_at.timestamp() if device.created_at else None,
    }


@router.get("/push/registrations")
async def list_push_registrations(
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List active push notification registrations."""
    rows = (
        await db.execute(
            select(PushDevice)
            .where(PushDevice.active.is_(True))
            .order_by(PushDevice.created_at)
        )
    ).scalars().all()

    return [
        {
            "id": str(d.id),
            "device_token": d.device_token,
            "platform": d.platform,
            "user_id": d.user_ref,
            "registered_at": d.created_at.timestamp() if d.created_at else None,
        }
        for d in rows
    ]


@router.post("/field-notes", status_code=201)
async def create_field_note(
    body: FieldNoteCreate,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Create a field note from mobile."""
    note = FieldNote(
        workspace_id=uuid.UUID(str(body.workspace_id)) if body.workspace_id else None,
        title=body.title,
        content=body.content,
        location=body.location,
        tags=body.tags,
        attachments=body.attachments,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return _serialise_note(note)


@router.get("/field-notes")
async def list_field_notes(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List field notes, oldest first."""
    rows = (
        await db.execute(
            _scoped_notes(select(FieldNote), workspace_id).order_by(
                FieldNote.created_at
            )
        )
    ).scalars().all()
    return [_serialise_note(n) for n in rows]


@router.get("/field-notes/{note_id}")
async def get_field_note(
    note_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get a field note."""
    try:
        nid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Field note not found")

    note = (
        await db.execute(select(FieldNote).where(FieldNote.id == nid))
    ).scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Field note not found")
    return _serialise_note(note)
