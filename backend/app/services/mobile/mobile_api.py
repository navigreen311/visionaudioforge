"""Mobile-optimized API service — compact payloads for operator mobile app."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus
from app.models.event import Event

logger = logging.getLogger(__name__)


class MobileAPIService:
    """Service layer providing mobile-optimised queries and actions."""

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    @staticmethod
    async def get_mobile_dashboard(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Return a compact mobile dashboard payload.

        Includes top-10 unresolved alerts, active stream count,
        user shifts, pending review count, and last 20 notifications.
        """
        # Top 10 unresolved alerts
        stmt = (
            select(Alert)
            .where(
                Alert.workspace_id == workspace_id,
                Alert.status.in_([AlertStatus.new, AlertStatus.acknowledged]),
            )
            .order_by(Alert.created_at.desc())
            .limit(10)
        )
        result = await db.execute(stmt)
        alerts = result.scalars().all()
        compact_alerts = [
            {
                "id": str(a.id),
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "payload_summary": (a.payload or {}).get("message", "")[:120] if a.payload else "",
            }
            for a in alerts
        ]

        # Active streams — count events of type 'stream_active' in last hour
        active_streams = 0  # Placeholder: real implementation counts RTSP sessions

        # Shifts — simplified stub (would query a shift table)
        my_shifts: list[dict] = []

        # Pending reviews
        pending_stmt = (
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.workspace_id == workspace_id,
                Alert.status == AlertStatus.new,
            )
        )
        pending_result = await db.execute(pending_stmt)
        pending_reviews = pending_result.scalar() or 0

        # Last 20 events as notifications proxy
        notif_stmt = (
            select(Event)
            .where(Event.workspace_id == workspace_id)
            .order_by(Event.timestamp.desc())
            .limit(20)
        )
        notif_result = await db.execute(notif_stmt)
        events = notif_result.scalars().all()
        notifications = [
            {
                "id": str(e.id),
                "type": e.type,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "summary": (e.payload or {}).get("message", e.type)[:100] if e.payload else e.type,
            }
            for e in events
        ]

        return {
            "alerts": compact_alerts,
            "active_streams": active_streams,
            "my_shifts": my_shifts,
            "pending_reviews": pending_reviews,
            "notifications": notifications,
        }

    # ------------------------------------------------------------------
    # Alert list (compact)
    # ------------------------------------------------------------------

    @staticmethod
    async def get_mobile_alerts(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return a compact alert list with optional status filter."""
        stmt = (
            select(Alert)
            .where(Alert.workspace_id == workspace_id)
            .order_by(Alert.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Alert.status == status)

        result = await db.execute(stmt)
        alerts = result.scalars().all()

        return [
            {
                "id": str(a.id),
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "thumbnail": (a.payload or {}).get("thumbnail_url"),
            }
            for a in alerts
        ]

    # ------------------------------------------------------------------
    # Acknowledge from mobile
    # ------------------------------------------------------------------

    @staticmethod
    async def acknowledge_mobile(
        db: AsyncSession,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
        location: Optional[dict] = None,
        photo: Optional[bytes] = None,
    ) -> dict[str, Any]:
        """Acknowledge an alert from the mobile app.

        Optionally records GPS location and photo evidence.
        """
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if alert is None:
            return {"acknowledged": False, "error": "Alert not found"}

        alert.status = AlertStatus.acknowledged
        alert.acknowledged_by = user_id

        # Persist location/photo metadata in payload
        meta: dict[str, Any] = dict(alert.payload or {})
        if location:
            meta["ack_location"] = location
        if photo:
            meta["ack_photo_size"] = len(photo)
        alert.payload = meta

        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        logger.info("Alert %s acknowledged by user %s (mobile)", alert_id, user_id)
        return {"acknowledged": True}

    # ------------------------------------------------------------------
    # Field evidence upload
    # ------------------------------------------------------------------

    @staticmethod
    async def upload_field_evidence(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        file_bytes: bytes,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle field evidence upload from mobile device.

        Stores metadata and returns an asset identifier.
        Real implementation would stream to object storage (MinIO/S3).
        """
        asset_id = str(uuid.uuid4())
        size_bytes = len(file_bytes)

        # Create an event recording the upload
        event = Event(
            id=uuid.uuid4(),
            type="field_evidence_upload",
            payload={
                "asset_id": asset_id,
                "user_id": str(user_id),
                "size_bytes": size_bytes,
                "metadata": metadata,
            },
            source="mobile_app",
            workspace_id=workspace_id,
        )
        db.add(event)
        await db.commit()

        logger.info("Field evidence uploaded: asset=%s size=%d", asset_id, size_bytes)
        return {"asset_id": asset_id, "uploaded": True}

    # ------------------------------------------------------------------
    # Offline package
    # ------------------------------------------------------------------

    @staticmethod
    async def get_offline_package(
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Build a data package for offline use.

        Includes alerts, cases (events of type 'case'), contacts,
        and an optional URL for a lightweight on-device model.
        """
        # Alerts
        alert_stmt = (
            select(Alert)
            .where(
                Alert.workspace_id == workspace_id,
                Alert.status.in_([AlertStatus.new, AlertStatus.acknowledged]),
            )
            .order_by(Alert.created_at.desc())
            .limit(100)
        )
        alert_result = await db.execute(alert_stmt)
        alerts = [
            {
                "id": str(a.id),
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "payload": a.payload,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alert_result.scalars().all()
        ]

        # Cases (events of type 'case')
        case_stmt = (
            select(Event)
            .where(Event.workspace_id == workspace_id, Event.type == "case")
            .order_by(Event.timestamp.desc())
            .limit(50)
        )
        case_result = await db.execute(case_stmt)
        cases = [
            {
                "id": str(e.id),
                "payload": e.payload,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in case_result.scalars().all()
        ]

        return {
            "alerts": alerts,
            "cases": cases,
            "contacts": [],  # Placeholder — no contacts model yet
            "offline_model_url": None,
            "last_sync": datetime.now(timezone.utc).isoformat(),
        }
