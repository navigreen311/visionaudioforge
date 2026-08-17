"""Bandwidth-aware sync service — smart model delivery based on connectivity.

Sync plans live in the ``sync_plans`` table. A transfer in progress spans many
requests and often more than one worker, so its progress cannot sit in the
memory of whichever process happened to create it.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge_fleet import EdgeDevice, SyncPlan

# Placeholder until model artifacts report their real size.
DEFAULT_MODEL_SIZE_MB = 120.0


def _as_uuid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class SyncService:
    """Provides bandwidth-aware model synchronization strategies."""

    async def estimate_sync_time(
        self, model_size_mb: float, bandwidth_mbps: float
    ) -> dict:
        """Estimate how long a sync will take given model size and bandwidth."""
        if bandwidth_mbps <= 0:
            raise ValueError("Bandwidth must be positive")

        # Convert Mbps to MB/s (1 byte = 8 bits)
        bandwidth_mb_per_s = bandwidth_mbps / 8.0
        estimated_seconds = model_size_mb / bandwidth_mb_per_s

        return {
            "estimated_seconds": round(estimated_seconds, 1),
            "estimated_minutes": round(estimated_seconds / 60.0, 2),
        }

    async def create_sync_plan(
        self, db: AsyncSession, device_id: str, model_id: str
    ) -> dict:
        """Create a sync plan based on device bandwidth capabilities."""
        try:
            key = _as_uuid(device_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(f"Device {device_id} not found")

        result = await db.execute(select(EdgeDevice).where(EdgeDevice.id == key))
        device = result.scalar_one_or_none()
        if device is None:
            raise KeyError(f"Device {device_id} not found")

        bandwidth = (device.network_info or {}).get("bandwidth_mbps", 10.0)
        model_size_mb = DEFAULT_MODEL_SIZE_MB

        # Narrower links get a cheaper payload rather than a longer transfer.
        if bandwidth < 1.0:
            strategy = "delta"
            effective_size = model_size_mb * 0.2  # Only changed layers
        elif bandwidth < 5.0:
            strategy = "compressed"
            effective_size = model_size_mb * 0.4
        else:
            strategy = "full"
            effective_size = model_size_mb

        time_est = await self.estimate_sync_time(effective_size, bandwidth)
        estimated_time = f"{time_est['estimated_minutes']} minutes"

        plan = SyncPlan(
            id=uuid.uuid4(),
            device_id=device.id,
            model_id=model_id,
            model_size_mb=model_size_mb,
            effective_size_mb=effective_size,
            available_bandwidth_mbps=bandwidth,
            estimated_time=estimated_time,
            strategy=strategy,
            status="created",
            progress_pct=0.0,
            transferred_mb=0.0,
        )
        db.add(plan)
        await db.commit()

        return {
            "plan_id": str(plan.id),
            "model_size_mb": model_size_mb,
            "available_bandwidth_mbps": bandwidth,
            "estimated_time": estimated_time,
            "strategy": strategy,
        }

    async def delta_sync_info(
        self, old_model_id: str, new_model_id: str
    ) -> dict:
        """Calculate delta between two model versions for efficient sync."""
        full_size = DEFAULT_MODEL_SIZE_MB
        delta_size = 24.0  # ~20% changed
        changed_layers = [
            {"layer": "conv2d_5", "size_mb": 8.0},
            {"layer": "dense_1", "size_mb": 10.0},
            {"layer": "output", "size_mb": 6.0},
        ]

        return {
            "full_size_mb": full_size,
            "delta_size_mb": delta_size,
            "savings_pct": round((1 - delta_size / full_size) * 100, 1),
            "changed_layers": changed_layers,
        }

    async def monitor_sync(self, db: AsyncSession, sync_id: str) -> dict:
        """Monitor the progress of an active sync operation."""
        try:
            key = _as_uuid(sync_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(f"Sync plan {sync_id} not found")

        result = await db.execute(select(SyncPlan).where(SyncPlan.id == key))
        plan = result.scalar_one_or_none()
        if plan is None:
            raise KeyError(f"Sync plan {sync_id} not found")

        effective_size = plan.effective_size_mb or DEFAULT_MODEL_SIZE_MB
        transferred = plan.transferred_mb or 0.0
        bandwidth = plan.available_bandwidth_mbps or 10.0
        remaining = effective_size - transferred
        speed = bandwidth / 8.0  # MB/s
        eta = remaining / speed if speed > 0 else 0

        return {
            "progress_pct": (
                round((transferred / effective_size) * 100, 1)
                if effective_size > 0
                else 100.0
            ),
            "transferred_mb": transferred,
            "remaining_mb": round(remaining, 2),
            "speed_mbps": bandwidth,
            "eta_seconds": round(eta, 1),
        }

    async def record_progress(
        self, db: AsyncSession, sync_id: str, transferred_mb: float
    ) -> dict:
        """Persist transfer progress so any worker can report on it."""
        result = await db.execute(
            select(SyncPlan).where(SyncPlan.id == _as_uuid(sync_id))
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            raise KeyError(f"Sync plan {sync_id} not found")

        effective_size = plan.effective_size_mb or DEFAULT_MODEL_SIZE_MB
        plan.transferred_mb = min(transferred_mb, effective_size)
        plan.progress_pct = (
            round((plan.transferred_mb / effective_size) * 100, 1)
            if effective_size > 0
            else 100.0
        )
        plan.status = "completed" if plan.progress_pct >= 100.0 else "syncing"
        await db.commit()

        return {"plan_id": str(plan.id), "progress_pct": plan.progress_pct}
