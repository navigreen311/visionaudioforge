"""EvidenceBundleService — collect, manage, and export evidence bundles.

Bundles are rows. A bundle that disappears on restart is not evidence, and one
that cannot be scoped to a workspace cannot be kept away from people who
should not see it — the previous in-memory store returned every bundle to
every caller because it had no workspace to filter on.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert
from app.models.evidence import EvidenceBundle, EvidenceBundleItem

logger = logging.getLogger(__name__)

BUNDLE_VERSION = "1.0"
BUNDLE_FORMAT = "evidence_bundle"

# asset_type -> the key it appears under in the exported bundle
_ITEM_BUCKETS = {"clip": "clips", "snapshot": "snapshots", "event": "events"}


def _as_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


class EvidenceBundleService:
    """Collects alert-related evidence into exportable bundles."""

    @staticmethod
    async def create_bundle(
        db: AsyncSession,
        alert_id: str,
        case_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create an evidence bundle for an alert.

        The alert is snapshotted into the bundle so the record reflects what
        was true when the evidence was collected.
        """
        now = datetime.now(timezone.utc)
        alert_snapshot: dict[str, Any] = {"alert_id": str(alert_id)}
        workspace = _as_uuid(workspace_id)

        alert_key = _as_uuid(alert_id)
        if alert_key is not None:
            result = await db.execute(select(Alert).where(Alert.id == alert_key))
            alert = result.scalar_one_or_none()
            if alert is not None:
                alert_snapshot = {
                    "alert_id": str(alert.id),
                    "rule_id": str(alert.rule_id),
                    "severity": getattr(alert.severity, "value", str(alert.severity)),
                    "status": getattr(alert.status, "value", str(alert.status)),
                    "payload": alert.payload or {},
                    "workspace_id": str(alert.workspace_id),
                    "created_at": _iso(alert.created_at) or now.isoformat(),
                }
                if workspace is None:
                    workspace = alert.workspace_id

        bundle = EvidenceBundle(
            id=uuid.uuid4(),
            workspace_id=workspace,
            alert_id=str(alert_id),
            case_id=case_id,
            alert_snapshot=alert_snapshot,
            bundle_metadata={
                "created_at": now.isoformat(),
                "case_id": case_id,
                "alert_id": str(alert_id),
                "version": BUNDLE_VERSION,
                "format": BUNDLE_FORMAT,
            },
        )
        db.add(bundle)
        await db.commit()

        logger.info("Created evidence bundle %s for alert %s", bundle.id, alert_id)
        return await EvidenceBundleService.get_bundle(db, str(bundle.id))

    @staticmethod
    async def _load(db: AsyncSession, bundle_id: str) -> EvidenceBundle:
        key = _as_uuid(bundle_id)
        if key is None:
            raise ValueError(f"Evidence bundle {bundle_id} not found")

        # populate_existing so a bundle already in the identity map picks up
        # items added since it was first loaded.
        result = await db.execute(
            select(EvidenceBundle)
            .options(selectinload(EvidenceBundle.items))
            .where(EvidenceBundle.id == key)
            .execution_options(populate_existing=True)
        )
        bundle = result.scalar_one_or_none()
        if bundle is None:
            raise ValueError(f"Evidence bundle {bundle_id} not found")
        return bundle

    @staticmethod
    def _serialise(bundle: EvidenceBundle) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "bundle_id": str(bundle.id),
            "alert": bundle.alert_snapshot or {},
            "clips": [],
            "snapshots": [],
            "events": [],
            "metadata": bundle.bundle_metadata or {},
        }

        for item in sorted(bundle.items, key=lambda i: i.added_at or datetime.min):
            entry = {"asset_id": item.asset_id, "added_at": _iso(item.added_at)}
            bucket = _ITEM_BUCKETS.get(item.asset_type)
            if bucket:
                payload[bucket].append(entry)
            else:
                payload.setdefault("other_assets", []).append(
                    {**entry, "type": item.asset_type}
                )

        return payload

    @staticmethod
    async def get_bundle(db: AsyncSession, bundle_id: str) -> dict[str, Any]:
        """Return a bundle with its attached assets."""
        return EvidenceBundleService._serialise(
            await EvidenceBundleService._load(db, bundle_id)
        )

    @staticmethod
    async def export_bundle(
        db: AsyncSession,
        bundle_id: str,
        format: str = "json",
    ) -> bytes:
        """Export a bundle as bytes.

        Raises:
            ValueError: If the bundle is unknown or the format unsupported.
        """
        if format not in ("json", "pdf_stub"):
            raise ValueError(f"Unsupported export format: {format}")

        bundle = EvidenceBundleService._serialise(
            await EvidenceBundleService._load(db, bundle_id)
        )

        export_metadata: dict[str, Any] = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": format,
        }
        if format == "pdf_stub":
            export_metadata["note"] = "PDF export requires reportlab library"

        return json.dumps(
            {**bundle, "export_metadata": export_metadata}, indent=2, default=str
        ).encode("utf-8")

    @staticmethod
    async def add_to_bundle(
        db: AsyncSession,
        bundle_id: str,
        asset_id: str,
        asset_type: str = "clip",
    ) -> dict[str, Any]:
        """Attach an asset to an existing bundle.

        Raises:
            ValueError: If the bundle is unknown.
        """
        bundle = await EvidenceBundleService._load(db, bundle_id)

        db.add(
            EvidenceBundleItem(
                id=uuid.uuid4(),
                bundle_id=bundle.id,
                asset_id=str(asset_id),
                asset_type=asset_type,
                added_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

        logger.info(
            "Added asset %s (type=%s) to bundle %s", asset_id, asset_type, bundle_id
        )
        return await EvidenceBundleService.get_bundle(db, bundle_id)

    @staticmethod
    async def list_bundles(
        db: AsyncSession,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        """List bundle summaries, scoped to a workspace when one is given."""
        query = select(EvidenceBundle).options(selectinload(EvidenceBundle.items))

        workspace = _as_uuid(workspace_id)
        if workspace is not None:
            query = query.where(EvidenceBundle.workspace_id == workspace)

        result = await db.execute(query.order_by(EvidenceBundle.created_at))

        summaries = []
        for bundle in result.scalars().all():
            items = bundle.items
            summaries.append(
                {
                    "bundle_id": str(bundle.id),
                    "alert_id": bundle.alert_id,
                    "case_id": bundle.case_id,
                    "created_at": (bundle.bundle_metadata or {}).get(
                        "created_at", _iso(bundle.created_at)
                    ),
                    "clip_count": sum(1 for i in items if i.asset_type == "clip"),
                    "snapshot_count": sum(
                        1 for i in items if i.asset_type == "snapshot"
                    ),
                    "event_count": sum(1 for i in items if i.asset_type == "event"),
                }
            )
        return summaries
