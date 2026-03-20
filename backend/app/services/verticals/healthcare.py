"""Healthcare vertical starter pack."""

from __future__ import annotations

from typing import Any

from app.services.verticals.base import VerticalPack


class HealthcareVerticalPack(VerticalPack):
    """Pre-built pipelines and alerts for healthcare / clinical deployments."""

    def info(self) -> dict[str, Any]:
        return {
            "name": "Healthcare",
            "slug": "healthcare",
            "icon": "heart-pulse",
            "description": "Patient monitoring, fall detection, hand-hygiene compliance, and clinical workflow analytics.",
            "category": "Healthcare",
        }

    def pipelines(self) -> dict[str, dict[str, Any]]:
        return {
            "fall_detection": {
                "name": "Fall Detection",
                "description": "Detect patient falls using motion analysis and alert staff.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 30}},
                    {"id": "flow_1", "type": "optical_flow", "params": {"method": "farneback"}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 0.7}},
                    {"id": "alert_1", "type": "alert", "params": {"message": "Fall detected", "severity": "critical"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "flow_1", "from_port": "output", "to_port": "input"},
                    {"from": "flow_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "hand_hygiene": {
                "name": "Hand Hygiene Compliance",
                "description": "Monitor hand-washing stations for compliance tracking.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 15}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.5}},
                    {"id": "log_1", "type": "log", "params": {"label": "hygiene_event"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "hygiene_log.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "log_1", "from_port": "output", "to_port": "input"},
                    {"from": "log_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
        }

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        return {
            "fall_detected": {
                "name": "Fall Detected",
                "severity": "critical",
                "conditions": {"motion_magnitude": {">": 0.7}, "direction": "downward"},
                "cooldown_seconds": 15,
            },
            "hygiene_violation": {
                "name": "Hygiene Non-Compliance",
                "severity": "warning",
                "conditions": {"compliance_score": {"<": 0.5}},
                "cooldown_seconds": 120,
            },
        }

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        return [
            {"type": "stat", "title": "Falls Today", "metric": "fall_count"},
            {"type": "chart", "title": "Hygiene Compliance Rate", "metric": "hygiene_rate"},
        ]

    def reports(self) -> dict[str, dict[str, Any]]:
        return {
            "daily_patient_safety": {"name": "Daily Patient Safety Report", "schedule": "daily"},
            "weekly_compliance": {"name": "Weekly Compliance Summary", "schedule": "weekly"},
        }
