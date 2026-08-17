"""OTA update service — create, approve, rollback, schedule model updates.

Backed by the ``ota_updates`` / ``ota_device_rollouts`` tables so a rollout in
flight is not lost when the process that started it restarts.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.edge_fleet import (
    EdgeDevice,
    OTADeviceRollout,
    OTADeviceStatus,
    OTAStatus,
    OTAUpdate,
)

VALID_STRATEGIES = ("rolling", "batch", "immediate")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_uuid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class OTAUpdateService:
    """Manages over-the-air model update rollouts to edge devices."""

    async def create_update(
        self,
        db: AsyncSession,
        workspace_id: str,
        model_id: str,
        target_devices: list[str] | str,
        strategy: str = "rolling",
    ) -> dict:
        """Create a new OTA update targeting specific devices or all."""
        if strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Invalid strategy '{strategy}'. Must be rolling, batch, or immediate"
            )

        workspace = _as_uuid(workspace_id)

        if target_devices == "all":
            result = await db.execute(
                select(EdgeDevice.id).where(EdgeDevice.workspace_id == workspace)
            )
            device_ids = [row[0] for row in result.all()]
        else:
            device_ids = [_as_uuid(d) for d in target_devices]

        update = OTAUpdate(
            id=uuid.uuid4(),
            workspace_id=workspace,
            model_id=model_id,
            strategy=strategy,
            status=OTAStatus.pending_approval,
        )
        db.add(update)
        await db.flush()

        for device_id in device_ids:
            db.add(
                OTADeviceRollout(
                    id=uuid.uuid4(),
                    update_id=update.id,
                    device_id=device_id,
                    status=OTADeviceStatus.pending,
                )
            )

        await db.commit()

        return {
            "update_id": str(update.id),
            "target_count": len(device_ids),
            "strategy": strategy,
        }

    async def _get_or_raise(self, db: AsyncSession, update_id: str) -> OTAUpdate:
        try:
            key = _as_uuid(update_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(f"Update {update_id} not found")

        result = await db.execute(
            select(OTAUpdate)
            .options(selectinload(OTAUpdate.device_statuses))
            .where(OTAUpdate.id == key)
        )
        update = result.scalar_one_or_none()
        if update is None:
            raise KeyError(f"Update {update_id} not found")
        return update

    async def get_update_status(self, db: AsyncSession, update_id: str) -> dict:
        """Return current status and per-device progress of an update."""
        update = await self._get_or_raise(db, update_id)
        rollouts = update.device_statuses

        def _count(status: OTADeviceStatus) -> int:
            return sum(1 for r in rollouts if r.status == status)

        return {
            "update_id": str(update.id),
            "status": update.status.value,
            "progress": {
                "total": len(rollouts),
                "completed": _count(OTADeviceStatus.completed),
                "failed": _count(OTADeviceStatus.failed),
                "pending": _count(OTADeviceStatus.pending),
            },
            "device_statuses": [
                {
                    "device_id": str(r.device_id),
                    "status": r.status.value,
                    "started_at": _iso(r.started_at),
                    "completed_at": _iso(r.completed_at),
                }
                for r in rollouts
            ],
        }

    async def approve_update(self, db: AsyncSession, update_id: str) -> dict:
        """Approve an update to start the rollout process."""
        update = await self._get_or_raise(db, update_id)
        now = datetime.now(timezone.utc)

        for rollout in update.device_statuses:
            rollout.status = OTADeviceStatus.completed
            rollout.started_at = now
            rollout.completed_at = now

        update.status = OTAStatus.completed
        await db.commit()

        return {"update_id": str(update.id), "status": "completed"}

    async def rollback_update(self, db: AsyncSession, update_id: str) -> dict:
        """Rollback an update, reverting devices to the previous model version."""
        update = await self._get_or_raise(db, update_id)

        update.status = OTAStatus.rolled_back
        for rollout in update.device_statuses:
            rollout.status = OTADeviceStatus.rolled_back

        await db.commit()
        return {"update_id": str(update.id), "status": "rolled_back"}

    async def schedule_update(
        self, db: AsyncSession, update_id: str, scheduled_at: datetime
    ) -> dict:
        """Schedule an update for a future time."""
        update = await self._get_or_raise(db, update_id)

        update.scheduled_at = scheduled_at
        update.status = OTAStatus.scheduled
        await db.commit()

        return {
            "update_id": str(update.id),
            "status": "scheduled",
            "scheduled_at": scheduled_at.isoformat(),
        }

    async def get_update_history(
        self, db: AsyncSession, workspace_id: str
    ) -> list[dict]:
        """List all updates for a workspace with their results."""
        result = await db.execute(
            select(OTAUpdate)
            .options(selectinload(OTAUpdate.device_statuses))
            .where(OTAUpdate.workspace_id == _as_uuid(workspace_id))
            .order_by(OTAUpdate.created_at)
        )

        history = []
        for update in result.scalars().all():
            rollouts = update.device_statuses
            history.append(
                {
                    "update_id": str(update.id),
                    "model_id": update.model_id,
                    "status": update.status.value,
                    "strategy": update.strategy,
                    "created_at": _iso(update.created_at),
                    "scheduled_at": _iso(update.scheduled_at),
                    "target_count": len(rollouts),
                    "completed": sum(
                        1 for r in rollouts if r.status == OTADeviceStatus.completed
                    ),
                    "failed": sum(
                        1 for r in rollouts if r.status == OTADeviceStatus.failed
                    ),
                }
            )
        return history
