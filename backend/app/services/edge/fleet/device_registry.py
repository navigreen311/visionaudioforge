"""Device registry — register, heartbeat, list, get, deregister edge devices.

Backed by the ``edge_devices`` / ``device_metrics`` tables. Registrations must
outlive a restart and be visible from every worker, so nothing here is cached
in module state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge_fleet import DeviceMetric, DeviceStatus, EdgeDevice

VALID_DEVICE_TYPES = frozenset(
    ["jetson_nano", "jetson_xavier", "raspberry_pi", "x86_server", "mobile", "browser"]
)

# Heartbeats retained per device. Older rows are trimmed on write so the
# telemetry table does not grow without bound.
METRICS_RETAINED = 100


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_uuid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class DeviceRegistry:
    """Manages the lifecycle of edge devices within a workspace."""

    async def register_device(
        self,
        db: AsyncSession,
        workspace_id: str,
        device_name: str,
        device_type: str,
        hardware_info: dict,
        network_info: dict | None = None,
    ) -> dict:
        """Register a new edge device and return its id + API key."""
        if device_type not in VALID_DEVICE_TYPES:
            raise ValueError(
                f"Invalid device_type '{device_type}'. "
                f"Must be one of {sorted(VALID_DEVICE_TYPES)}"
            )

        api_key = f"vaf_dk_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)

        device = EdgeDevice(
            id=uuid.uuid4(),
            workspace_id=_as_uuid(workspace_id),
            device_name=device_name,
            device_type=device_type,
            hardware_info=hardware_info or {},
            network_info=network_info or {},
            api_key=api_key,
            status=DeviceStatus.online,
            last_seen=now,
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)

        return {
            "device_id": str(device.id),
            "api_key": api_key,
            "registered_at": _iso(device.created_at) or now.isoformat(),
        }

    async def _get_or_raise(self, db: AsyncSession, device_id: str) -> EdgeDevice:
        try:
            key = _as_uuid(device_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(f"Device {device_id} not found")

        result = await db.execute(select(EdgeDevice).where(EdgeDevice.id == key))
        device = result.scalar_one_or_none()
        if device is None:
            raise KeyError(f"Device {device_id} not found")
        return device

    async def heartbeat(
        self, db: AsyncSession, device_id: str, status_payload: dict
    ) -> dict:
        """Update last_seen and record this heartbeat's system metrics."""
        device = await self._get_or_raise(db, device_id)

        now = datetime.now(timezone.utc)
        device.last_seen = now
        device.status = DeviceStatus.online

        db.add(
            DeviceMetric(
                id=uuid.uuid4(),
                device_id=device.id,
                timestamp=now,
                payload=dict(status_payload),
            )
        )
        await db.flush()
        await self._trim_metrics(db, device.id)
        await db.commit()

        return {"acknowledged": True}

    async def _trim_metrics(self, db: AsyncSession, device_id: uuid.UUID) -> None:
        """Keep only the newest ``METRICS_RETAINED`` heartbeats for a device."""
        keep = select(DeviceMetric.id).where(
            DeviceMetric.device_id == device_id
        ).order_by(DeviceMetric.timestamp.desc()).limit(METRICS_RETAINED)

        await db.execute(
            delete(DeviceMetric).where(
                DeviceMetric.device_id == device_id,
                DeviceMetric.id.notin_(keep.scalar_subquery()),
            )
        )

    async def list_devices(
        self, db: AsyncSession, workspace_id: str, status: str | None = None
    ) -> list[dict]:
        """List devices in a workspace, optionally filtered by status."""
        query = select(EdgeDevice).where(
            EdgeDevice.workspace_id == _as_uuid(workspace_id)
        )
        if status:
            query = query.where(EdgeDevice.status == DeviceStatus(status))

        result = await db.execute(query.order_by(EdgeDevice.created_at))
        return [
            {
                "device_id": str(d.id),
                "device_name": d.device_name,
                "device_type": d.device_type,
                "status": d.status.value,
                "last_seen": _iso(d.last_seen),
                "hardware_info": d.hardware_info,
            }
            for d in result.scalars().all()
        ]

    async def get_device(self, db: AsyncSession, device_id: str) -> dict:
        """Return full device details including recent metrics history."""
        device = await self._get_or_raise(db, device_id)
        history = await self.recent_metrics(db, device.id, limit=20)

        return {
            "device_id": str(device.id),
            "workspace_id": str(device.workspace_id),
            "device_name": device.device_name,
            "device_type": device.device_type,
            "status": device.status.value,
            "last_seen": _iso(device.last_seen),
            "registered_at": _iso(device.created_at),
            "hardware_info": device.hardware_info,
            "network_info": device.network_info,
            "metrics_history": history,
        }

    async def recent_metrics(
        self, db: AsyncSession, device_id: uuid.UUID, limit: int = 20
    ) -> list[dict]:
        """Return the newest heartbeats for a device, oldest first."""
        result = await db.execute(
            select(DeviceMetric)
            .where(DeviceMetric.device_id == device_id)
            .order_by(DeviceMetric.timestamp.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return [{"timestamp": _iso(m.timestamp), **(m.payload or {})} for m in rows]

    async def latest_metrics(
        self, db: AsyncSession, device_id: uuid.UUID
    ) -> dict:
        """Return the most recent heartbeat payload, or ``{}`` if never seen."""
        result = await db.execute(
            select(DeviceMetric)
            .where(DeviceMetric.device_id == device_id)
            .order_by(DeviceMetric.timestamp.desc())
            .limit(1)
        )
        metric = result.scalar_one_or_none()
        return dict(metric.payload or {}) if metric else {}

    async def deregister_device(self, db: AsyncSession, device_id: str) -> bool:
        """Remove a device from the registry."""
        try:
            device = await self._get_or_raise(db, device_id)
        except KeyError:
            return False

        await db.delete(device)
        await db.commit()
        return True

    async def get_fleet_overview(
        self, db: AsyncSession, workspace_id: str
    ) -> dict:
        """Aggregate fleet-level statistics for a workspace."""
        workspace = _as_uuid(workspace_id)

        result = await db.execute(
            select(EdgeDevice.device_type, EdgeDevice.status, func.count())
            .where(EdgeDevice.workspace_id == workspace)
            .group_by(EdgeDevice.device_type, EdgeDevice.status)
        )

        by_type: dict[str, int] = {}
        total = 0
        online = 0
        for device_type, status, count in result.all():
            by_type[device_type] = by_type.get(device_type, 0) + count
            total += count
            if status == DeviceStatus.online:
                online += count

        cpu_values: list[float] = []
        mem_values: list[float] = []
        devices = await db.execute(
            select(EdgeDevice.id).where(EdgeDevice.workspace_id == workspace)
        )
        for (device_id,) in devices.all():
            latest = await self.latest_metrics(db, device_id)
            if "cpu_pct" in latest:
                cpu_values.append(latest["cpu_pct"])
            if "memory_pct" in latest:
                mem_values.append(latest["memory_pct"])

        return {
            "total_devices": total,
            "online": online,
            "offline": total - online,
            "by_type": by_type,
            "avg_cpu_pct": round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else 0.0,
            "avg_memory_pct": round(sum(mem_values) / len(mem_values), 1) if mem_values else 0.0,
        }
