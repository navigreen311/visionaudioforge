"""Industrial Inspection vertical starter pack."""

from __future__ import annotations

from typing import Any

from app.services.verticals.base import VerticalPack


class IndustrialVerticalPack(VerticalPack):
    """Pre-built pipelines and alerts for industrial / manufacturing deployments.

    Covers equipment inspection, PPE safety compliance, vibration monitoring,
    production-line throughput, and environmental sound monitoring.
    """

    def info(self) -> dict[str, Any]:
        return {
            "name": "Industrial Inspection",
            "slug": "industrial",
            "icon": "factory",
            "description": (
                "Equipment defect detection, PPE compliance, vibration analysis, "
                "production-line monitoring, and environmental sound classification."
            ),
            "category": "Manufacturing",
        }

    # ------------------------------------------------------------------
    # Pipelines
    # ------------------------------------------------------------------

    def pipelines(self) -> dict[str, dict[str, Any]]:
        return {
            "equipment_inspection": {
                "name": "Equipment Inspection",
                "description": "Capture equipment image, detect defects, compute anomaly score, and generate report.",
                "nodes": [
                    {"id": "input_1", "type": "input_image", "params": {"path": ""}},
                    {"id": "normalize_1", "type": "normalize", "params": {"method": "z_score"}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.6}},
                    {"id": "edge_1", "type": "edge_detect", "params": {"low_threshold": 30, "high_threshold": 120}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "inspection_report.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "normalize_1", "from_port": "output", "to_port": "input"},
                    {"from": "normalize_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "edge_1", "from_port": "output", "to_port": "input"},
                    {"from": "edge_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "safety_compliance": {
                "name": "Safety Compliance (PPE Detection)",
                "description": "Detect PPE (helmet, vest, goggles) and alert when missing.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 15}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.5}},
                    {"id": "cond_1", "type": "conditional", "params": {"condition": "ppe_missing"}},
                    {"id": "alert_1", "type": "alert", "params": {"message": "PPE violation — protective equipment not detected", "severity": "critical"}},
                    {"id": "log_1", "type": "log", "params": {"label": "ppe_check"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "cond_1", "from_port": "output", "to_port": "input"},
                    {"from": "cond_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                    {"from": "alert_1", "to": "log_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "vibration_monitoring": {
                "name": "Vibration Monitoring",
                "description": "Analyze machine audio for spectral anomalies indicating wear or failure.",
                "nodes": [
                    {"id": "input_1", "type": "input_audio", "params": {"path": ""}},
                    {"id": "stft_1", "type": "stft", "params": {"n_fft": 2048}},
                    {"id": "mel_1", "type": "mel_spectrogram", "params": {"n_mels": 128}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 0.7}},
                    {"id": "alert_1", "type": "alert", "params": {"message": "Vibration anomaly detected", "severity": "high"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "stft_1", "from_port": "output", "to_port": "input"},
                    {"from": "stft_1", "to": "mel_1", "from_port": "output", "to_port": "input"},
                    {"from": "mel_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "production_line_monitoring": {
                "name": "Production Line Monitoring",
                "description": "Count products on the line, measure throughput, and flag slow-downs.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 30}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.5}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 0.3}},
                    {"id": "log_1", "type": "log", "params": {"label": "throughput"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "production_throughput.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "log_1", "from_port": "output", "to_port": "input"},
                    {"from": "log_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "environmental_monitoring": {
                "name": "Environmental Monitoring",
                "description": "Classify environmental sounds and detect anomalous noise levels.",
                "nodes": [
                    {"id": "input_1", "type": "input_audio", "params": {"path": ""}},
                    {"id": "mel_1", "type": "mel_spectrogram", "params": {"n_mels": 64}},
                    {"id": "mfcc_1", "type": "mfcc", "params": {"n_mfcc": 13}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 0.8}},
                    {"id": "alert_1", "type": "alert", "params": {"message": "Abnormal noise level detected", "severity": "warning"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "mel_1", "from_port": "output", "to_port": "input"},
                    {"from": "mel_1", "to": "mfcc_1", "from_port": "output", "to_port": "input"},
                    {"from": "mfcc_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                ],
            },
        }

    # ------------------------------------------------------------------
    # Alert presets
    # ------------------------------------------------------------------

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        return {
            "ppe_violation": {
                "name": "PPE Violation",
                "severity": "critical",
                "conditions": {"ppe_detected": False, "zone": "production_floor"},
                "cooldown_seconds": 15,
            },
            "equipment_anomaly": {
                "name": "Equipment Anomaly",
                "severity": "high",
                "conditions": {"anomaly_score": {">": 0.75}},
                "cooldown_seconds": 60,
            },
            "production_slowdown": {
                "name": "Production Slowdown",
                "severity": "medium",
                "conditions": {"throughput_ratio": {"<": 0.7}},
                "cooldown_seconds": 300,
            },
            "noise_level_exceeded": {
                "name": "Noise Level Exceeded",
                "severity": "medium",
                "conditions": {"db_level": {">": 85}},
                "cooldown_seconds": 120,
            },
        }

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        return [
            {"type": "chart", "title": "Production Throughput", "metric": "units_per_hour"},
            {"type": "gauge", "title": "Equipment Health", "metric": "equipment_health_score"},
            {"type": "stat", "title": "Safety Compliance Rate", "metric": "ppe_compliance_pct"},
            {"type": "chart", "title": "Defect Rate", "metric": "defect_rate_trend"},
        ]

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def reports(self) -> dict[str, dict[str, Any]]:
        return {
            "shift_production_report": {
                "name": "Shift Production Report",
                "schedule": "per_shift",
                "sections": ["throughput", "defect_count", "downtime_minutes"],
            },
            "safety_audit": {
                "name": "Safety Audit",
                "schedule": "daily",
                "sections": ["ppe_violations", "incident_log", "compliance_rate"],
            },
            "maintenance_prediction": {
                "name": "Maintenance Prediction",
                "schedule": "weekly",
                "sections": ["anomaly_trends", "predicted_failures", "recommended_actions"],
            },
            "quality_inspection": {
                "name": "Quality Inspection",
                "schedule": "daily",
                "sections": ["defect_classification", "reject_rate", "root_cause_analysis"],
            },
        }
