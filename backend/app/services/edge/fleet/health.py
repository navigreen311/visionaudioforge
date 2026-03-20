"""Device health service — monitoring, alerting, and fleet health aggregation."""

from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta
from typing import Any

from app.services.edge.fleet.device_registry import _devices


class DeviceHealthService:
    """Monitors device health metrics and detects unhealthy devices."""

    async def get_device_health(self, db: Any, device_id: str) -> dict:
        """Return current health snapshot for a device."""
        device = _devices.get(device_id)
        if device is None:
            raise KeyError(f"Device {device_id} not found")

        # Pull latest metrics from history or generate defaults
        metrics = device["metrics_history"][-1] if device["metrics_history"] else {}

        now = datetime.now(timezone.utc)
        registered = datetime.fromisoformat(device["registered_at"])
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

    async def get_fleet_health(self, db: Any, workspace_id: str) -> dict:
        """Return aggregated health metrics for the entire fleet."""
        ws_devices = [d for d in _devices.values() if d["workspace_id"] == workspace_id]

        if not ws_devices:
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

        for device in ws_devices:
            metrics = device["metrics_history"][-1] if device["metrics_history"] else {}
            cpu = metrics.get("cpu_pct", 0.0)
            mem = metrics.get("memory_pct", 0.0)
            disk = metrics.get("disk_pct", 0.0)

            cpu_vals.append(cpu)
            mem_vals.append(mem)
            disk_vals.append(disk)
            total_inferences += metrics.get("inference_count_24h", 0)
            total_errors += metrics.get("error_count_24h", 0)

            if cpu > 90 or mem > 90 or disk > 95:
                unhealthy += 1

        total = len(ws_devices)
        return {
            "total_devices": total,
            "healthy": total - unhealthy,
            "unhealthy": unhealthy,
            "avg_cpu_pct": round(sum(cpu_vals) / len(cpu_vals), 1),
            "avg_memory_pct": round(sum(mem_vals) / len(mem_vals), 1),
            "avg_disk_pct": round(sum(disk_vals) / len(disk_vals), 1),
            "total_inference_24h": total_inferences,
            "total_errors_24h": total_errors,
        }

    async def detect_unhealthy_devices(
        self, db: Any, workspace_id: str
    ) -> list[dict]:
        """Detect devices with health issues: high CPU, low disk, offline > 1h."""
        ws_devices = [d for d in _devices.values() if d["workspace_id"] == workspace_id]
        now = datetime.now(timezone.utc)
        issues: list[dict] = []

        for device in ws_devices:
            device_issues: list[str] = []
            metrics = device["metrics_history"][-1] if device["metrics_history"] else {}

            if metrics.get("cpu_pct", 0) > 90:
                device_issues.append("high_cpu")
            if metrics.get("memory_pct", 0) > 90:
                device_issues.append("high_memory")
            if metrics.get("disk_pct", 0) > 95:
                device_issues.append("low_disk")

            last_seen = datetime.fromisoformat(device["last_seen"])
            if (now - last_seen) > timedelta(hours=1):
                device_issues.append("offline_over_1h")
                # Mark the device as offline
                device["status"] = "offline"

            if device_issues:
                issues.append({
                    "device_id": device["device_id"],
                    "device_name": device["device_name"],
                    "issues": device_issues,
                    "last_seen": device["last_seen"],
                })

        return issues

    async def device_health_history(
        self, db: Any, device_id: str, hours: int = 24
    ) -> list[dict]:
        """Return time-series health data for a device over the given period."""
        device = _devices.get(device_id)
        if device is None:
            raise KeyError(f"Device {device_id} not found")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        results = []
        for entry in device["metrics_history"]:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts >= cutoff:
                results.append(entry)

        return results
