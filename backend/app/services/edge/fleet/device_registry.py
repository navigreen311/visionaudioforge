"""Device registry — register, heartbeat, list, get, deregister edge devices."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


# In-memory store keyed by device_id
_devices: dict[str, dict[str, Any]] = {}

VALID_DEVICE_TYPES = frozenset(
    ["jetson_nano", "jetson_xavier", "raspberry_pi", "x86_server", "mobile", "browser"]
)


class DeviceRegistry:
    """Manages the lifecycle of edge devices within a workspace."""

    async def register_device(
        self,
        db: Any,
        workspace_id: str,
        device_name: str,
        device_type: str,
        hardware_info: dict,
        network_info: dict | None = None,
    ) -> dict:
        """Register a new edge device and return its id + API key."""
        if device_type not in VALID_DEVICE_TYPES:
            raise ValueError(f"Invalid device_type '{device_type}'. Must be one of {sorted(VALID_DEVICE_TYPES)}")

        device_id = str(uuid.uuid4())
        api_key = f"vaf_dk_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)

        device_record = {
            "device_id": device_id,
            "workspace_id": workspace_id,
            "device_name": device_name,
            "device_type": device_type,
            "hardware_info": hardware_info,
            "network_info": network_info or {},
            "api_key": api_key,
            "registered_at": now.isoformat(),
            "last_seen": now.isoformat(),
            "status": "online",
            "metrics_history": [],
        }
        _devices[device_id] = device_record

        return {
            "device_id": device_id,
            "api_key": api_key,
            "registered_at": now.isoformat(),
        }

    async def heartbeat(
        self, db: Any, device_id: str, status_payload: dict
    ) -> dict:
        """Update last_seen timestamp and record system metrics."""
        device = _devices.get(device_id)
        if device is None:
            raise KeyError(f"Device {device_id} not found")

        now = datetime.now(timezone.utc)
        device["last_seen"] = now.isoformat()
        device["status"] = "online"

        metrics_entry = {
            "timestamp": now.isoformat(),
            **status_payload,
        }
        device["metrics_history"].append(metrics_entry)
        # Keep last 100 entries
        if len(device["metrics_history"]) > 100:
            device["metrics_history"] = device["metrics_history"][-100:]

        return {"acknowledged": True}

    async def list_devices(
        self, db: Any, workspace_id: str, status: str | None = None
    ) -> list[dict]:
        """List devices in a workspace, optionally filtered by status."""
        results = []
        for d in _devices.values():
            if d["workspace_id"] != workspace_id:
                continue
            if status and d["status"] != status:
                continue
            results.append({
                "device_id": d["device_id"],
                "device_name": d["device_name"],
                "device_type": d["device_type"],
                "status": d["status"],
                "last_seen": d["last_seen"],
                "hardware_info": d["hardware_info"],
            })
        return results

    async def get_device(self, db: Any, device_id: str) -> dict:
        """Return full device details including recent metrics history."""
        device = _devices.get(device_id)
        if device is None:
            raise KeyError(f"Device {device_id} not found")
        return {
            "device_id": device["device_id"],
            "workspace_id": device["workspace_id"],
            "device_name": device["device_name"],
            "device_type": device["device_type"],
            "status": device["status"],
            "last_seen": device["last_seen"],
            "registered_at": device["registered_at"],
            "hardware_info": device["hardware_info"],
            "network_info": device["network_info"],
            "metrics_history": device["metrics_history"][-20:],
        }

    async def deregister_device(self, db: Any, device_id: str) -> bool:
        """Remove a device from the registry."""
        if device_id in _devices:
            del _devices[device_id]
            return True
        return False

    async def get_fleet_overview(self, db: Any, workspace_id: str) -> dict:
        """Aggregate fleet-level statistics for a workspace."""
        ws_devices = [d for d in _devices.values() if d["workspace_id"] == workspace_id]
        total = len(ws_devices)
        online = sum(1 for d in ws_devices if d["status"] == "online")
        offline = total - online

        by_type: dict[str, int] = {}
        for d in ws_devices:
            by_type[d["device_type"]] = by_type.get(d["device_type"], 0) + 1

        cpu_values: list[float] = []
        mem_values: list[float] = []
        for d in ws_devices:
            if d["metrics_history"]:
                latest = d["metrics_history"][-1]
                if "cpu_pct" in latest:
                    cpu_values.append(latest["cpu_pct"])
                if "memory_pct" in latest:
                    mem_values.append(latest["memory_pct"])

        return {
            "total_devices": total,
            "online": online,
            "offline": offline,
            "by_type": by_type,
            "avg_cpu_pct": round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else 0.0,
            "avg_memory_pct": round(sum(mem_values) / len(mem_values), 1) if mem_values else 0.0,
        }
