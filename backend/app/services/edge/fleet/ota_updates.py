"""OTA update service — create, approve, rollback, schedule model updates."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.edge.fleet.device_registry import _devices

# In-memory store keyed by update_id
_updates: dict[str, dict[str, Any]] = {}


class OTAUpdateService:
    """Manages over-the-air model update rollouts to edge devices."""

    async def create_update(
        self,
        db: Any,
        workspace_id: str,
        model_id: str,
        target_devices: list[str] | str,
        strategy: str = "rolling",
    ) -> dict:
        """Create a new OTA update targeting specific devices or all."""
        if strategy not in ("rolling", "batch", "immediate"):
            raise ValueError(f"Invalid strategy '{strategy}'. Must be rolling, batch, or immediate")

        if target_devices == "all":
            device_ids = [
                d["device_id"]
                for d in _devices.values()
                if d["workspace_id"] == workspace_id
            ]
        else:
            device_ids = list(target_devices)

        update_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        device_statuses = [
            {"device_id": did, "status": "pending", "started_at": None, "completed_at": None}
            for did in device_ids
        ]

        _updates[update_id] = {
            "update_id": update_id,
            "workspace_id": workspace_id,
            "model_id": model_id,
            "strategy": strategy,
            "status": "pending_approval",
            "created_at": now.isoformat(),
            "scheduled_at": None,
            "device_statuses": device_statuses,
            "previous_model_id": None,
        }

        return {
            "update_id": update_id,
            "target_count": len(device_ids),
            "strategy": strategy,
        }

    async def get_update_status(self, db: Any, update_id: str) -> dict:
        """Return current status and per-device progress of an update."""
        update = _updates.get(update_id)
        if update is None:
            raise KeyError(f"Update {update_id} not found")

        ds = update["device_statuses"]
        completed = sum(1 for d in ds if d["status"] == "completed")
        failed = sum(1 for d in ds if d["status"] == "failed")
        pending = sum(1 for d in ds if d["status"] == "pending")

        return {
            "update_id": update_id,
            "status": update["status"],
            "progress": {
                "total": len(ds),
                "completed": completed,
                "failed": failed,
                "pending": pending,
            },
            "device_statuses": ds,
        }

    async def approve_update(self, db: Any, update_id: str) -> dict:
        """Approve an update to start the rollout process."""
        update = _updates.get(update_id)
        if update is None:
            raise KeyError(f"Update {update_id} not found")

        now = datetime.now(timezone.utc)
        update["status"] = "in_progress"

        # Simulate immediate completion for all targeted devices
        for ds in update["device_statuses"]:
            ds["status"] = "completed"
            ds["started_at"] = now.isoformat()
            ds["completed_at"] = now.isoformat()

        update["status"] = "completed"
        return {"update_id": update_id, "status": "completed"}

    async def rollback_update(self, db: Any, update_id: str) -> dict:
        """Rollback an update, reverting devices to the previous model version."""
        update = _updates.get(update_id)
        if update is None:
            raise KeyError(f"Update {update_id} not found")

        update["status"] = "rolled_back"
        for ds in update["device_statuses"]:
            ds["status"] = "rolled_back"

        return {"update_id": update_id, "status": "rolled_back"}

    async def schedule_update(
        self, db: Any, update_id: str, scheduled_at: datetime
    ) -> dict:
        """Schedule an update for a future time."""
        update = _updates.get(update_id)
        if update is None:
            raise KeyError(f"Update {update_id} not found")

        update["scheduled_at"] = scheduled_at.isoformat()
        update["status"] = "scheduled"

        return {
            "update_id": update_id,
            "status": "scheduled",
            "scheduled_at": scheduled_at.isoformat(),
        }

    async def get_update_history(self, db: Any, workspace_id: str) -> list[dict]:
        """List all updates for a workspace with their results."""
        results = []
        for u in _updates.values():
            if u["workspace_id"] != workspace_id:
                continue
            ds = u["device_statuses"]
            results.append({
                "update_id": u["update_id"],
                "model_id": u["model_id"],
                "status": u["status"],
                "strategy": u["strategy"],
                "created_at": u["created_at"],
                "scheduled_at": u["scheduled_at"],
                "target_count": len(ds),
                "completed": sum(1 for d in ds if d["status"] == "completed"),
                "failed": sum(1 for d in ds if d["status"] == "failed"),
            })
        return results
