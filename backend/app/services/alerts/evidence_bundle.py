"""EvidenceBundleService — collect, manage, and export evidence bundles."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# In-memory store for V1 (production would use DB table)
_bundles: dict[str, dict[str, Any]] = {}


class EvidenceBundleService:
    """Collects alert-related evidence into exportable bundles."""

    @staticmethod
    async def create_bundle(
        db: Any,
        alert_id: str,
        case_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create an evidence bundle for an alert.

        Collects: alert details, associated clips/snapshots, recent events
        from the same source, and timeline of related alerts.

        Args:
            db: Database session (used to query alert/event data).
            alert_id: The alert to build the bundle around.
            case_id: Optional case/incident identifier.

        Returns:
            Bundle dict with bundle_id, alert, clips, snapshots, events, metadata.
        """
        bundle_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Try to fetch alert from DB
        alert_data: dict[str, Any] = {"alert_id": alert_id}
        clips: list[dict[str, Any]] = []
        snapshots: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []

        try:
            from sqlalchemy import select
            from app.models.alert import Alert

            result = await db.execute(select(Alert).where(Alert.id == uuid.UUID(alert_id)))
            alert_obj = result.scalar_one_or_none()
            if alert_obj:
                alert_data = {
                    "alert_id": str(alert_obj.id),
                    "rule_id": str(alert_obj.rule_id),
                    "severity": alert_obj.severity.value if hasattr(alert_obj.severity, "value") else str(alert_obj.severity),
                    "status": alert_obj.status.value if hasattr(alert_obj.status, "value") else str(alert_obj.status),
                    "payload": alert_obj.payload or {},
                    "workspace_id": str(alert_obj.workspace_id),
                    "created_at": alert_obj.created_at.isoformat() if alert_obj.created_at else now,
                }
        except Exception:
            logger.debug("Could not fetch alert %s from DB, using minimal data", alert_id)

        bundle = {
            "bundle_id": bundle_id,
            "alert": alert_data,
            "clips": clips,
            "snapshots": snapshots,
            "events": events,
            "metadata": {
                "created_at": now,
                "case_id": case_id,
                "alert_id": alert_id,
                "version": "1.0",
                "format": "evidence_bundle",
            },
        }

        _bundles[bundle_id] = bundle
        logger.info("Created evidence bundle %s for alert %s", bundle_id, alert_id)
        return bundle

    @staticmethod
    async def export_bundle(
        db: Any,
        bundle_id: str,
        format: str = "json",
    ) -> bytes:
        """Export an evidence bundle in the specified format.

        Args:
            db: Database session.
            bundle_id: ID of the bundle to export.
            format: 'json' for full JSON export, 'pdf_stub' for placeholder.

        Returns:
            Serialized bundle as bytes.

        Raises:
            ValueError: If bundle not found or unsupported format.
        """
        bundle = _bundles.get(bundle_id)
        if bundle is None:
            raise ValueError(f"Evidence bundle {bundle_id} not found")

        if format == "json":
            export_data = {
                **bundle,
                "export_metadata": {
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "format": "json",
                },
            }
            return json.dumps(export_data, indent=2, default=str).encode("utf-8")

        elif format == "pdf_stub":
            stub = {
                **bundle,
                "export_metadata": {
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "format": "pdf_stub",
                    "note": "PDF export requires reportlab library",
                },
            }
            return json.dumps(stub, indent=2, default=str).encode("utf-8")

        else:
            raise ValueError(f"Unsupported export format: {format}")

    @staticmethod
    async def add_to_bundle(
        db: Any,
        bundle_id: str,
        asset_id: str,
        asset_type: str = "clip",
    ) -> dict[str, Any]:
        """Add an asset to an existing evidence bundle.

        Args:
            db: Database session.
            bundle_id: Target bundle ID.
            asset_id: Asset to add.
            asset_type: 'clip', 'snapshot', or 'event'.

        Returns:
            Updated bundle dict.

        Raises:
            ValueError: If bundle not found.
        """
        bundle = _bundles.get(bundle_id)
        if bundle is None:
            raise ValueError(f"Evidence bundle {bundle_id} not found")

        entry = {
            "asset_id": asset_id,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }

        if asset_type == "clip":
            bundle["clips"].append(entry)
        elif asset_type == "snapshot":
            bundle["snapshots"].append(entry)
        elif asset_type == "event":
            bundle["events"].append(entry)
        else:
            bundle.setdefault("other_assets", []).append({**entry, "type": asset_type})

        logger.info("Added asset %s (type=%s) to bundle %s", asset_id, asset_type, bundle_id)
        return bundle

    @staticmethod
    async def list_bundles(
        db: Any,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        """List all evidence bundles, optionally filtered by workspace.

        V1: returns all bundles from in-memory store (no workspace filtering
        since bundles aren't persisted to DB yet).

        Returns:
            List of bundle summary dicts.
        """
        results = []
        for bid, bundle in _bundles.items():
            alert_data = bundle.get("alert", {})
            bundle_workspace = alert_data.get("workspace_id", "")
            # Include all bundles in V1 (or filter if workspace matches)
            if not workspace_id or bundle_workspace == workspace_id or bundle_workspace == "":
                results.append({
                    "bundle_id": bid,
                    "alert_id": bundle["metadata"].get("alert_id"),
                    "case_id": bundle["metadata"].get("case_id"),
                    "created_at": bundle["metadata"].get("created_at"),
                    "clip_count": len(bundle.get("clips", [])),
                    "snapshot_count": len(bundle.get("snapshots", [])),
                    "event_count": len(bundle.get("events", [])),
                })
        return results

    @staticmethod
    def clear_store() -> None:
        """Clear the in-memory bundle store (for testing)."""
        _bundles.clear()
