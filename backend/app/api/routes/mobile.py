"""Mobile Backend routes — dashboard, push notifications, field notes."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_push_registrations: list[dict] = []
_field_notes: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def get_dashboard() -> dict[str, Any]:
    """Get mobile-optimized dashboard summary."""
    return {
        "active_streams": 3,
        "recent_alerts": 2,
        "pending_reviews": 5,
        "field_notes": len(_field_notes),
        "system_status": "operational",
        "last_updated": time.time(),
    }


@router.post("/push/register")
async def register_push(body: PushRegister) -> dict[str, Any]:
    """Register a device for push notifications."""
    registration = {
        "id": str(uuid.uuid4()),
        "device_token": body.device_token,
        "platform": body.platform,
        "user_id": body.user_id,
        "registered_at": time.time(),
    }
    _push_registrations.append(registration)
    return registration


@router.get("/push/registrations")
async def list_push_registrations() -> list[dict]:
    """List push notification registrations."""
    return _push_registrations


@router.post("/field-notes")
async def create_field_note(body: FieldNoteCreate) -> dict[str, Any]:
    """Create a field note from mobile."""
    nid = str(uuid.uuid4())
    note = {
        "id": nid,
        "title": body.title,
        "content": body.content,
        "location": body.location,
        "tags": body.tags,
        "attachments": body.attachments,
        "created_at": time.time(),
    }
    _field_notes[nid] = note
    return note


@router.get("/field-notes")
async def list_field_notes() -> list[dict]:
    """List all field notes."""
    return list(_field_notes.values())


@router.get("/field-notes/{note_id}")
async def get_field_note(note_id: str) -> dict:
    """Get a field note."""
    if note_id not in _field_notes:
        raise HTTPException(status_code=404, detail="Field note not found")
    return _field_notes[note_id]
