"""Field annotation service — notes, photos, and location tracking for operators."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event

logger = logging.getLogger(__name__)

# In-memory location history (replace with DB/time-series store in production)
_location_history: dict[str, list[dict[str, Any]]] = {}  # user_id -> [points]


class FieldAnnotationService:
    """Create and retrieve field notes, photos, and operator location data."""

    # ------------------------------------------------------------------
    # Field note
    # ------------------------------------------------------------------

    @staticmethod
    async def create_field_note(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        location: Optional[dict[str, float]] = None,
        attached_asset_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a field note event.

        Args:
            location: ``{"latitude": float, "longitude": float, "accuracy_m": float}``
            attached_asset_id: optional asset reference
        """
        event_id = uuid.uuid4()
        payload: dict[str, Any] = {
            "content": content,
            "user_id": str(user_id),
        }
        if location:
            payload["location"] = location
            _record_location(user_id, location)
        if attached_asset_id:
            payload["attached_asset_id"] = attached_asset_id

        linked_ids = [uuid.UUID(attached_asset_id)] if attached_asset_id else None

        event = Event(
            id=event_id,
            type="field_note",
            payload=payload,
            source="mobile_app",
            workspace_id=workspace_id,
            linked_asset_ids=linked_ids,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        logger.info("Field note created: %s by user %s", event_id, user_id)
        return {
            "id": str(event.id),
            "type": event.type,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

    # ------------------------------------------------------------------
    # Field photo
    # ------------------------------------------------------------------

    @staticmethod
    async def create_field_photo(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        photo_bytes: bytes,
        notes: str,
        location: Optional[dict[str, float]] = None,
    ) -> dict[str, Any]:
        """Create a field photo asset with an accompanying event.

        In production this would upload ``photo_bytes`` to object storage.
        Here we record metadata and return a generated asset ID.
        """
        asset_id = str(uuid.uuid4())
        size_bytes = len(photo_bytes)

        payload: dict[str, Any] = {
            "asset_id": asset_id,
            "user_id": str(user_id),
            "notes": notes,
            "size_bytes": size_bytes,
        }
        if location:
            payload["location"] = location
            _record_location(user_id, location)

        event = Event(
            id=uuid.uuid4(),
            type="field_photo",
            payload=payload,
            source="mobile_app",
            workspace_id=workspace_id,
            linked_asset_ids=[uuid.UUID(asset_id)],
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        logger.info("Field photo created: asset=%s by user %s", asset_id, user_id)
        return {
            "asset_id": asset_id,
            "event_id": str(event.id),
            "size_bytes": size_bytes,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

    # ------------------------------------------------------------------
    # List field notes
    # ------------------------------------------------------------------

    @staticmethod
    async def get_field_notes(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve field notes for a workspace with optional time range."""
        stmt = (
            select(Event)
            .where(
                Event.workspace_id == workspace_id,
                Event.type == "field_note",
            )
            .order_by(Event.timestamp.desc())
            .limit(100)
        )
        if start:
            stmt = stmt.where(Event.timestamp >= start)
        if end:
            stmt = stmt.where(Event.timestamp <= end)

        result = await db.execute(stmt)
        return [
            {
                "id": str(e.id),
                "payload": e.payload,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "location": (e.payload or {}).get("location"),
            }
            for e in result.scalars().all()
        ]

    # ------------------------------------------------------------------
    # Location history
    # ------------------------------------------------------------------

    @staticmethod
    async def get_location_history(
        db: AsyncSession,
        user_id: uuid.UUID,
        hours: int = 8,
    ) -> list[dict[str, Any]]:
        """Return location points for an operator within the last *hours*."""
        uid = str(user_id)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        points = _location_history.get(uid, [])
        return [p for p in points if p.get("timestamp", "") >= cutoff.isoformat()]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record_location(user_id: uuid.UUID, location: dict[str, float]) -> None:
    """Append a location point to the in-memory history."""
    uid = str(user_id)
    if uid not in _location_history:
        _location_history[uid] = []
    _location_history[uid].append(
        {
            **location,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
