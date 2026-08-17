"""Offline sync service — incremental data packages and conflict resolution."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus
from app.models.event import Event
from app.models.integration import SyncConflict

logger = logging.getLogger(__name__)

# Conflicts live in sync_conflicts. An unresolved conflict is exactly the
# state that must not be lost: dropping one silently discards an edit
# somebody made in the field.


class OfflineSyncService:
    """Manage offline data synchronisation for the mobile app."""

    # ------------------------------------------------------------------
    # Create sync package
    # ------------------------------------------------------------------

    @staticmethod
    async def create_sync_package(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        last_sync_at: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Build an incremental sync package.

        Only includes data changed since *last_sync_at*.  When
        ``last_sync_at`` is ``None`` a full package is returned.
        """
        package_id = str(uuid.uuid4())
        sync_token = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # --- Alerts ---
        alert_stmt = (
            select(Alert)
            .where(Alert.workspace_id == workspace_id)
            .order_by(Alert.created_at.desc())
            .limit(200)
        )
        if last_sync_at:
            alert_stmt = alert_stmt.where(Alert.updated_at > last_sync_at)
        alert_result = await db.execute(alert_stmt)
        new_alerts = [
            {
                "id": str(a.id),
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "payload": a.payload,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
            for a in alert_result.scalars().all()
        ]

        # --- Events (as updated cases / new events) ---
        event_stmt = (
            select(Event)
            .where(Event.workspace_id == workspace_id)
            .order_by(Event.timestamp.desc())
            .limit(200)
        )
        if last_sync_at:
            event_stmt = event_stmt.where(Event.timestamp > last_sync_at)
        event_result = await db.execute(event_stmt)
        events_list = [
            {
                "id": str(e.id),
                "type": e.type,
                "payload": e.payload,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in event_result.scalars().all()
        ]

        # Separate case-type events
        updated_cases = [e for e in events_list if e["type"] == "case"]
        new_events = [e for e in events_list if e["type"] != "case"]

        import json

        payload_bytes = json.dumps(
            {"alerts": new_alerts, "cases": updated_cases, "events": new_events}
        ).encode()

        return {
            "package_id": package_id,
            "new_alerts": new_alerts,
            "updated_cases": updated_cases,
            "new_events": new_events,
            "sync_token": sync_token,
            "size_bytes": len(payload_bytes),
        }

    # ------------------------------------------------------------------
    # Process offline actions
    # ------------------------------------------------------------------

    @staticmethod
    async def process_offline_actions(
        db: AsyncSession,
        actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Process a batch of actions queued while the device was offline.

        Supported action types:
        - acknowledge_alert
        - add_note
        - upload_evidence
        - annotate

        Conflicts are detected when an alert was resolved by another
        user while the device was offline.
        """
        processed = 0
        failed = 0
        conflicts: list[dict[str, Any]] = []

        for action in actions:
            action_type = action.get("type", "")
            try:
                if action_type == "acknowledge_alert":
                    alert_id = uuid.UUID(action["alert_id"])
                    result = await db.execute(select(Alert).where(Alert.id == alert_id))
                    alert = result.scalar_one_or_none()

                    if alert is None:
                        failed += 1
                        continue

                    # Conflict: alert already resolved/dismissed
                    if alert.status in (AlertStatus.resolved, AlertStatus.dismissed):
                        row = SyncConflict(
                            id=uuid.uuid4(),
                            workspace_id=alert.workspace_id,
                            entity_type="alert",
                            entity_id=str(alert_id),
                            local_version=action,
                            server_version={"status": alert.status.value},
                        )
                        db.add(row)
                        await db.flush()

                        conflicts.append(
                            {
                                "conflict_id": str(row.id),
                                "action": action,
                                "reason": (
                                    f"Alert already {alert.status.value} "
                                    "by another user"
                                ),
                                "current_status": alert.status.value,
                            }
                        )
                        continue

                    alert.status = AlertStatus.acknowledged
                    if "user_id" in action:
                        alert.acknowledged_by = uuid.UUID(action["user_id"])
                    db.add(alert)
                    processed += 1

                elif action_type == "add_note":
                    event = Event(
                        id=uuid.uuid4(),
                        type="field_note",
                        payload=action.get("payload", {}),
                        source="mobile_offline",
                        workspace_id=uuid.UUID(action["workspace_id"]),
                    )
                    db.add(event)
                    processed += 1

                elif action_type == "upload_evidence":
                    event = Event(
                        id=uuid.uuid4(),
                        type="field_evidence_upload",
                        payload=action.get("payload", {}),
                        source="mobile_offline",
                        workspace_id=uuid.UUID(action["workspace_id"]),
                    )
                    db.add(event)
                    processed += 1

                elif action_type == "annotate":
                    event = Event(
                        id=uuid.uuid4(),
                        type="field_annotation",
                        payload=action.get("payload", {}),
                        source="mobile_offline",
                        workspace_id=uuid.UUID(action["workspace_id"]),
                    )
                    db.add(event)
                    processed += 1

                else:
                    logger.warning("Unknown offline action type: %s", action_type)
                    failed += 1

            except Exception:
                logger.exception("Failed to process offline action: %s", action)
                failed += 1

        await db.commit()
        return {"processed": processed, "failed": failed, "conflicts": conflicts}

    # ------------------------------------------------------------------
    # Resolve conflict
    # ------------------------------------------------------------------

    @staticmethod
    async def resolve_sync_conflict(
        db: AsyncSession,
        conflict_id: str,
        resolution: str,
    ) -> dict[str, Any]:
        """Resolve a sync conflict.

        resolution: 'accept_server' | 'force_local' | 'dismiss'
        """
        try:
            key = uuid.UUID(conflict_id)
        except (ValueError, AttributeError, TypeError):
            return {"resolved": False, "error": "Conflict not found"}

        result = await db.execute(
            select(SyncConflict).where(SyncConflict.id == key)
        )
        conflict = result.scalar_one_or_none()
        if conflict is None or conflict.resolution is not None:
            return {"resolved": False, "error": "Conflict not found"}

        conflict.resolution = resolution
        conflict.resolved_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info("Conflict %s resolved with: %s", conflict_id, resolution)
        return {"resolved": True, "conflict_id": conflict_id, "resolution": resolution}

    # ------------------------------------------------------------------
    # List conflicts
    # ------------------------------------------------------------------

    @staticmethod
    async def list_conflicts(
        db: AsyncSession,
        workspace_id: uuid.UUID | None = None,
        unresolved_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Return sync conflicts, newest first.

        Unresolved conflicts are work waiting on a human decision, so they are
        the default view.
        """
        query = select(SyncConflict).order_by(SyncConflict.created_at.desc())
        if workspace_id is not None:
            query = query.where(SyncConflict.workspace_id == workspace_id)
        if unresolved_only:
            query = query.where(SyncConflict.resolution.is_(None))

        result = await db.execute(query)
        return [
            {
                "conflict_id": str(c.id),
                "entity_type": c.entity_type,
                "entity_id": c.entity_id,
                "local_version": c.local_version,
                "server_version": c.server_version,
                "resolution": c.resolution,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in result.scalars().all()
        ]
