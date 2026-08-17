"""Device health service — monitoring, alerting, and fleet health aggregation.

Reads telemetry from the ``device_metrics`` table rather than a process-local
cache, so any worker reports the same picture of the fleet.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge_fleet import DeviceMetric, DeviceStatus, EdgeDevice

# Thresholds above which a device is considered unhealthy.
CPU_LIMIT_PCT = 90
MEMORY_LIMIT_PCT = 90
DISK_LIMIT_PCT = 95
OFFLINE_AFTER = timedelta(hours=1)


def _as_uuid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class DeviceHealthService:
    """Monitors device health metrics and detects unhealthy devices."""

    async def _latest_metric(
        self, db: AsyncSession, device_id: uuid.UUID
    ) -> dict:
        result = await db.execute(
            select(DeviceMetric)
            .where(DeviceMetric.device_id == device_id)
            .order_by(DeviceMetric.timestamp.desc())
            .limit(1)
        )
        metric = result.scalar_one_or_none()
        return dict(metric.payload or {}) if metric else {}

    async def _workspace_devices(
        self, db: AsyncSession, workspace_id: str
    ) -> list[EdgeDevice]:
        result = await db.execute(
            select(EdgeDevice).where(
                EdgeDevice.workspace_id == _as_uuid(workspace_id)
            )
        )
        return list(result.scalars().all())

    async def get_device_health(
        self, db: AsyncSession, device_id: str
    ) -> dict:
        """Return current health snapshot for a device."""
        try:
            key = _as_uuid(device_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(f"Device {device_id} not found")

        result = await db.execute(select(EdgeDevice).where(EdgeDevice.id == key))
        device = result.scalar_one_or_none()
        if device is None:
            raise KeyError(f"Device {device_id} not found")

        metrics = await self._latest_metric(db, device.id)
        now = datetime.now(timezone.utc)
        registered = device.created_at or now
        if registered.tzinfo is None:
            registered = registered.replace(tzinfo=timezone.utc)
        uptime_hours = (now - registered).total_seconds() / 3600.0

        return {
            "cpu_pct": metrics.get("cpu_pct", 0.0),
            "memory_pct": metrics.get("memory_pct", 0.0),
            "disk_pct": metrics.get("disk_pct", 0.0),
            "gpu_pct": metrics.get("gpu_pct"),
            "temperature_c": metrics.get("temperature_c"),
            "uptime_hours": round(uptime_hours, 2),
            "model_version": metrics.get("model_version", "unknown"),
            "last_inference_at": metrics.get("last_inference_at", now.isoformat()),
            "inference_count_24h": metrics.get("inference_count_24h", 0),
            "error_count_24h": metrics.get("error_count_24h", 0),
        }

    async def get_fleet_health(
        self, db: AsyncSession, workspace_id: str
    ) -> dict:
        """Return aggregated health metrics for the entire fleet."""
        devices = await self._workspace_devices(db, workspace_id)

        if not devices:
            return {
                "total_devices": 0,
                "healthy": 0,
                "unhealthy": 0,
                "avg_cpu_pct": 0.0,
                "avg_memory_pct": 0.0,
                "avg_disk_pct": 0.0,
                "total_inference_24h": 0,
                "total_errors_24h": 0,
            }

        cpu_vals, mem_vals, disk_vals = [], [], []
        total_inferences = 0
        total_errors = 0
        unhealthy = 0

        for device in devices:
            metrics = await self._latest_metric(db, device.id)
            cpu = metrics.get("cpu_pct", 0.0)
            mem = metrics.get("memory_pct", 0.0)
            disk = metrics.get("disk_pct", 0.0)

            cpu_vals.append(cpu)
            mem_vals.append(mem)
            disk_vals.append(disk)
            total_inferences += metrics.get("inference_count_24h", 0)
            total_errors += metrics.get("error_count_24h", 0)

            if cpu > CPU_LIMIT_PCT or mem > MEMORY_LIMIT_PCT or disk > DISK_LIMIT_PCT:
                unhealthy += 1

        total = len(devices)
        return {
            "total_devices": total,
            "healthy": total - unhealthy,
            "unhealthy": unhealthy,
            "avg_cpu_pct": round(sum(cpu_vals) / total, 1),
            "avg_memory_pct": round(sum(mem_vals) / total, 1),
            "avg_disk_pct": round(sum(disk_vals) / total, 1),
            "total_inference_24h": total_inferences,
            "total_errors_24h": total_errors,
        }

    async def detect_unhealthy_devices(
        self, db: AsyncSession, workspace_id: str
    ) -> list[dict]:
        """Detect devices with high CPU/memory, low disk, or offline > 1h.

        A device past the offline threshold is marked offline, so the fleet
        view reflects it without waiting for the device to report in.
        """
        devices = await self._workspace_devices(db, workspace_id)
        now = datetime.now(timezone.utc)
        issues: list[dict] = []
        changed = False

        for device in devices:
            metrics = await self._latest_metric(db, device.id)
            device_issues: list[str] = []

            if metrics.get("cpu_pct", 0) > CPU_LIMIT_PCT:
                device_issues.append("high_cpu")
            if metrics.get("memory_pct", 0) > MEMORY_LIMIT_PCT:
                device_issues.append("high_memory")
            if metrics.get("disk_pct", 0) > DISK_LIMIT_PCT:
                device_issues.append("low_disk")

            last_seen = device.last_seen or now
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            if (now - last_seen) > OFFLINE_AFTER:
                device_issues.append("offline_over_1h")
                if device.status != DeviceStatus.offline:
                    device.status = DeviceStatus.offline
                    changed = True

            if device_issues:
                issues.append(
                    {
                        "device_id": str(device.id),
                        "device_name": device.device_name,
                        "issues": device_issues,
                        "last_seen": _iso(last_seen),
                    }
                )

        if changed:
            await db.commit()

        return issues

    async def device_health_history(
        self, db: AsyncSession, device_id: str, hours: int = 24
    ) -> list[dict]:
        """Return time-series health data for a device over the given period."""
        try:
            key = _as_uuid(device_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(f"Device {device_id} not found")

        exists = await db.execute(
            select(EdgeDevice.id).where(EdgeDevice.id == key)
        )
        if exists.scalar_one_or_none() is None:
            raise KeyError(f"Device {device_id} not found")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(DeviceMetric)
            .where(DeviceMetric.device_id == key, DeviceMetric.timestamp >= cutoff)
            .order_by(DeviceMetric.timestamp)
        )
        return [
            {"timestamp": _iso(m.timestamp), **(m.payload or {})}
            for m in result.scalars().all()
        ]
