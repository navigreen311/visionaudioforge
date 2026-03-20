"""Bandwidth-aware sync service — smart model delivery based on connectivity."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.edge.fleet.device_registry import _devices

# In-memory sync plans
_sync_plans: dict[str, dict[str, Any]] = {}


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
        self, db: Any, device_id: str, model_id: str
    ) -> dict:
        """Create a sync plan based on device bandwidth capabilities."""
        device = _devices.get(device_id)
        if device is None:
            raise KeyError(f"Device {device_id} not found")

        # Get bandwidth from device network info or default
        net_info = device.get("network_info", {})
        bandwidth = net_info.get("bandwidth_mbps", 10.0)

        # Simulated model size
        model_size_mb = 120.0

        # Select strategy based on bandwidth
        if bandwidth < 1.0:
            strategy = "delta"
            effective_size = model_size_mb * 0.2  # Only changed layers
        elif bandwidth < 5.0:
            strategy = "compressed"
            effective_size = model_size_mb * 0.4  # Compressed
        else:
            strategy = "full"
            effective_size = model_size_mb

        time_est = await self.estimate_sync_time(effective_size, bandwidth)

        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        plan = {
            "plan_id": plan_id,
            "device_id": device_id,
            "model_id": model_id,
            "model_size_mb": model_size_mb,
            "effective_size_mb": effective_size,
            "available_bandwidth_mbps": bandwidth,
            "estimated_time": f"{time_est['estimated_minutes']} minutes",
            "strategy": strategy,
            "created_at": now.isoformat(),
            "status": "created",
            "progress_pct": 0.0,
            "transferred_mb": 0.0,
        }
        _sync_plans[plan_id] = plan

        return {
            "plan_id": plan_id,
            "model_size_mb": model_size_mb,
            "available_bandwidth_mbps": bandwidth,
            "estimated_time": f"{time_est['estimated_minutes']} minutes",
            "strategy": strategy,
        }

    async def delta_sync_info(
        self, old_model_id: str, new_model_id: str
    ) -> dict:
        """Calculate delta between two model versions for efficient sync."""
        # Simulated delta computation
        full_size = 120.0
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

    async def monitor_sync(self, sync_id: str) -> dict:
        """Monitor the progress of an active sync operation."""
        plan = _sync_plans.get(sync_id)
        if plan is None:
            raise KeyError(f"Sync plan {sync_id} not found")

        effective_size = plan.get("effective_size_mb", 120.0)
        transferred = plan.get("transferred_mb", 0.0)
        bandwidth = plan.get("available_bandwidth_mbps", 10.0)
        remaining = effective_size - transferred
        speed = bandwidth / 8.0  # MB/s
        eta = remaining / speed if speed > 0 else 0

        return {
            "progress_pct": round((transferred / effective_size) * 100, 1) if effective_size > 0 else 100.0,
            "transferred_mb": transferred,
            "remaining_mb": round(remaining, 2),
            "speed_mbps": bandwidth,
            "eta_seconds": round(eta, 1),
        }
