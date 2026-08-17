"""Remote config service — per-device and fleet-wide configuration management.

Backed by the append-only ``device_configs`` table: the highest
``config_version`` per device is current, earlier rows are the audit history.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge_fleet import DeviceConfig, EdgeDevice

DEFAULT_CONFIG: dict = {
    "inference_settings": {
        "confidence_threshold": 0.5,
        "max_batch": 4,
    },
    "capture_settings": {
        "fps": 15,
        "resolution": "720p",
    },
    "sync_settings": {
        "sync_interval_s": 300,
        "bandwidth_limit_mbps": 10.0,
    },
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_uuid(value) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class RemoteConfigService:
    """Manages remote configuration for individual devices and fleets."""

    async def _device_or_raise(
        self, db: AsyncSession, device_id: str
    ) -> EdgeDevice:
        try:
            key = _as_uuid(device_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(f"Device {device_id} not found")

        result = await db.execute(select(EdgeDevice).where(EdgeDevice.id == key))
        device = result.scalar_one_or_none()
        if device is None:
            raise KeyError(f"Device {device_id} not found")
        return device

    async def _next_version(self, db: AsyncSession, device_id: uuid.UUID) -> int:
        result = await db.execute(
            select(func.max(DeviceConfig.config_version)).where(
                DeviceConfig.device_id == device_id
            )
        )
        return int(result.scalar() or 0) + 1

    async def set_config(
        self, db: AsyncSession, device_id: str, config: dict
    ) -> dict:
        """Set or update configuration for a specific device."""
        device = await self._device_or_raise(db, device_id)

        now = datetime.now(timezone.utc)
        version = await self._next_version(db, device.id)

        db.add(
            DeviceConfig(
                id=uuid.uuid4(),
                device_id=device.id,
                config_version=version,
                config=config,
                updated_at=now,
            )
        )
        await db.commit()

        return {"config_version": version, "updated_at": now.isoformat()}

    async def get_config(self, db: AsyncSession, device_id: str) -> dict:
        """Get the current configuration for a device."""
        device = await self._device_or_raise(db, device_id)

        result = await db.execute(
            select(DeviceConfig)
            .where(DeviceConfig.device_id == device.id)
            .order_by(DeviceConfig.config_version.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        if latest is None:
            return {
                "config_version": 0,
                "config": DEFAULT_CONFIG.copy(),
                "updated_at": None,
            }

        return {
            "config_version": latest.config_version,
            "config": latest.config,
            "updated_at": _iso(latest.updated_at),
        }

    async def set_fleet_config(
        self, db: AsyncSession, workspace_id: str, config: dict
    ) -> dict:
        """Apply configuration to all devices in a workspace."""
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(EdgeDevice.id).where(
                EdgeDevice.workspace_id == _as_uuid(workspace_id)
            )
        )
        device_ids = [row[0] for row in result.all()]

        for device_id in device_ids:
            version = await self._next_version(db, device_id)
            db.add(
                DeviceConfig(
                    id=uuid.uuid4(),
                    device_id=device_id,
                    config_version=version,
                    config=config,
                    updated_at=now,
                )
            )
            await db.flush()

        await db.commit()
        return {"updated_devices": len(device_ids), "updated_at": now.isoformat()}

    async def get_config_diff(self, db: AsyncSession, device_id: str) -> dict:
        """Return the diff between a device's current and previous config."""
        device = await self._device_or_raise(db, device_id)

        result = await db.execute(
            select(DeviceConfig)
            .where(DeviceConfig.device_id == device.id)
            .order_by(DeviceConfig.config_version.desc())
            .limit(2)
        )
        rows = list(result.scalars().all())
        if len(rows) < 2:
            return {"has_diff": False, "changes": []}

        current, previous = rows[0].config or {}, rows[1].config or {}

        changes: list[dict] = []
        for key in sorted(set(previous) | set(current)):
            old_val, new_val = previous.get(key), current.get(key)
            if old_val != new_val:
                changes.append({"key": key, "old": old_val, "new": new_val})

        return {"has_diff": bool(changes), "changes": changes}

    async def config_history(
        self, db: AsyncSession, device_id: str
    ) -> list[dict]:
        """Return the full configuration version history for a device."""
        device = await self._device_or_raise(db, device_id)

        result = await db.execute(
            select(DeviceConfig)
            .where(DeviceConfig.device_id == device.id)
            .order_by(DeviceConfig.config_version)
        )
        return [
            {
                "config_version": row.config_version,
                "config": row.config,
                "updated_at": _iso(row.updated_at),
            }
            for row in result.scalars().all()
        ]
