"""Security vertical starter pack."""

from __future__ import annotations

from typing import Any

from app.services.verticals.base import VerticalPack


class SecurityVerticalPack(VerticalPack):
    """Pre-built pipelines and alerts for security / surveillance deployments."""

    def info(self) -> dict[str, Any]:
        return {
            "name": "Security & Surveillance",
            "slug": "security",
            "icon": "shield",
            "description": "Perimeter monitoring, intrusion detection, license plate recognition, and incident management.",
            "category": "Public Safety",
        }

    def pipelines(self) -> dict[str, dict[str, Any]]:
        return {
            "perimeter_monitoring": {
                "name": "Perimeter Monitoring",
                "description": "Detect motion at facility perimeters and alert on intrusion.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 30}},
                    {"id": "diff_1", "type": "frame_diff", "params": {}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 0.15}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.5}},
                    {"id": "alert_1", "type": "alert", "params": {"message": "Perimeter breach detected", "severity": "critical"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "diff_1", "from_port": "output", "to_port": "input"},
                    {"from": "diff_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "license_plate_recognition": {
                "name": "License Plate Recognition",
                "description": "Detect and read license plates from camera feeds.",
                "nodes": [
                    {"id": "input_1", "type": "input_image", "params": {"path": ""}},
                    {"id": "normalize_1", "type": "normalize", "params": {"method": "min_max"}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.6}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "plates.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "normalize_1", "from_port": "output", "to_port": "input"},
                    {"from": "normalize_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
        }

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        return {
            "intrusion_detected": {
                "name": "Intrusion Detected",
                "severity": "critical",
                "conditions": {"motion_score": {">": 0.8}, "zone": "perimeter"},
                "cooldown_seconds": 30,
            },
            "loitering": {
                "name": "Loitering Alert",
                "severity": "warning",
                "conditions": {"dwell_time_seconds": {">": 120}},
                "cooldown_seconds": 60,
            },
        }

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        return [
            {"type": "chart", "title": "Incidents Over Time", "metric": "incident_count"},
            {"type": "map", "title": "Camera Coverage", "metric": "camera_status"},
            {"type": "stat", "title": "Active Alerts", "metric": "active_alert_count"},
        ]

    def reports(self) -> dict[str, dict[str, Any]]:
        return {
            "daily_incident": {"name": "Daily Incident Report", "schedule": "daily"},
            "weekly_security": {"name": "Weekly Security Summary", "schedule": "weekly"},
        }
