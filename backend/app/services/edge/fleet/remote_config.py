"""Remote config service — per-device and fleet-wide configuration management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.edge.fleet.device_registry import _devices

# In-memory config store: device_id → list of config versions
_configs: dict[str, list[dict[str, Any]]] = {}

DEFAULT_CONFIG: dict[str, Any] = {
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


class RemoteConfigService:
    """Manages remote configuration for individual devices and fleets."""

    async def set_config(self, db: Any, device_id: str, config: dict) -> dict:
        """Set or update configuration for a specific device."""
        if device_id not in _devices:
            raise KeyError(f"Device {device_id} not found")

        now = datetime.now(timezone.utc)
        history = _configs.setdefault(device_id, [])
        version = len(history) + 1

        entry = {
            "config_version": version,
            "config": config,
            "updated_at": now.isoformat(),
        }
        history.append(entry)

        return {
            "config_version": version,
            "updated_at": now.isoformat(),
        }

    async def get_config(self, db: Any, device_id: str) -> dict:
        """Get the current configuration for a device."""
        if device_id not in _devices:
            raise KeyError(f"Device {device_id} not found")

        history = _configs.get(device_id, [])
        if not history:
            return {
                "config_version": 0,
                "config": DEFAULT_CONFIG.copy(),
                "updated_at": None,
            }
        latest = history[-1]
        return {
            "config_version": latest["config_version"],
            "config": latest["config"],
            "updated_at": latest["updated_at"],
        }

    async def set_fleet_config(
        self, db: Any, workspace_id: str, config: dict
    ) -> dict:
        """Apply configuration to all devices in a workspace."""
        now = datetime.now(timezone.utc)
        updated_count = 0

        for device in _devices.values():
            if device["workspace_id"] != workspace_id:
                continue
            did = device["device_id"]
            history = _configs.setdefault(did, [])
            version = len(history) + 1
            history.append({
                "config_version": version,
                "config": config,
                "updated_at": now.isoformat(),
            })
            updated_count += 1

        return {
            "updated_devices": updated_count,
            "updated_at": now.isoformat(),
        }

    async def get_config_diff(self, db: Any, device_id: str) -> dict:
        """Return the diff between a device's current and previous config."""
        if device_id not in _devices:
            raise KeyError(f"Device {device_id} not found")

        history = _configs.get(device_id, [])
        if len(history) < 2:
            return {"has_diff": False, "changes": []}

        prev_cfg = history[-2]["config"]
        curr_cfg = history[-1]["config"]

        changes: list[dict] = []
        all_keys = set(list(prev_cfg.keys()) + list(curr_cfg.keys()))
        for key in sorted(all_keys):
            old_val = prev_cfg.get(key)
            new_val = curr_cfg.get(key)
            if old_val != new_val:
                changes.append({"key": key, "old": old_val, "new": new_val})

        return {"has_diff": len(changes) > 0, "changes": changes}

    async def config_history(self, db: Any, device_id: str) -> list[dict]:
        """Return the full configuration version history for a device."""
        if device_id not in _devices:
            raise KeyError(f"Device {device_id} not found")

        return _configs.get(device_id, [])
