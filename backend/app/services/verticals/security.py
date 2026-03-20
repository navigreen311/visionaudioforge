"""Security & Surveillance vertical pack — pipelines, alert presets, dashboards, and report templates."""

from __future__ import annotations


class SecurityVerticalPack:
    """Pre-configured resources for security/surveillance operations."""

    PACK_INFO = {
        "name": "Security & Surveillance",
        "version": "1.0",
        "description": (
            "Pre-configured pipelines, alert rules, and dashboards for security operations"
        ),
        "modules_used": ["capture", "vision", "alerts", "investigation", "search"],
    }

    # ------------------------------------------------------------------
    # Pipeline templates
    # ------------------------------------------------------------------

    @staticmethod
    def get_pipeline_templates() -> list[dict]:
        """Return five security-focused pipeline templates."""
        return [
            {
                "name": "perimeter_monitoring",
                "description": "Detect persons or vehicles breaching the perimeter",
                "steps": [
                    {"type": "InputVideo"},
                    {"type": "DetectObjects", "params": {"classes": ["person", "vehicle"]}},
                    {"type": "FrameDiff", "params": {"threshold": 15}},
                    {"type": "Filter", "params": {"condition": "motion", "operator": ">", "value": 5}},
                    {
                        "type": "Alert",
                        "params": {
                            "severity": "high",
                            "message": "Perimeter breach detected",
                        },
                    },
                ],
            },
            {
                "name": "intrusion_detection",
                "description": "Detect and track new objects entering a monitored zone",
                "steps": [
                    {"type": "InputVideo"},
                    {"type": "DetectObjects", "params": {}},
                    {"type": "Tracking", "params": {}},
                    {"type": "Filter", "params": {"condition": "new_object_in_zone"}},
                    {"type": "Alert", "params": {"severity": "critical", "message": "Intrusion detected"}},
                    {"type": "AutoClip", "params": {"pre_seconds": 10, "post_seconds": 30}},
                ],
            },
            {
                "name": "loitering_detection",
                "description": "Alert when a person lingers in an area beyond threshold",
                "steps": [
                    {"type": "InputVideo"},
                    {"type": "DetectObjects", "params": {"classes": ["person"]}},
                    {"type": "Tracking", "params": {}},
                    {"type": "LoiteringCheck", "params": {"threshold_seconds": 120}},
                    {"type": "Alert", "params": {"severity": "medium", "message": "Loitering detected"}},
                ],
            },
            {
                "name": "vehicle_monitoring",
                "description": "Track vehicles and read license plates",
                "steps": [
                    {"type": "InputVideo"},
                    {"type": "DetectObjects", "params": {"classes": ["vehicle"]}},
                    {"type": "LicensePlateOCR", "params": {}},
                    {"type": "Log", "params": {}},
                    {
                        "type": "Alert",
                        "params": {
                            "severity": "high",
                            "condition": "if_unauthorized",
                            "message": "Unauthorized vehicle detected",
                        },
                    },
                ],
            },
            {
                "name": "crowd_density",
                "description": "Alert when crowd size exceeds threshold",
                "steps": [
                    {"type": "InputVideo"},
                    {"type": "DetectObjects", "params": {"classes": ["person"]}},
                    {"type": "CountFilter", "params": {"threshold": 20}},
                    {"type": "Alert", "params": {"severity": "medium", "message": "Crowd density threshold exceeded"}},
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Alert presets
    # ------------------------------------------------------------------

    @staticmethod
    def get_alert_presets() -> list[dict]:
        """Return pre-configured alert rules for security operations."""
        return [
            {
                "name": "unauthorized_access",
                "description": "Triggers when any person is detected in a restricted zone",
                "conditions": {
                    "type": "threshold",
                    "metric": "person_count_in_restricted_zone",
                    "operator": ">",
                    "value": 0,
                },
                "severity": "critical",
                "actions": ["webhook", "slack"],
            },
            {
                "name": "camera_tampering",
                "description": "Triggers on sudden brightness changes indicating tampering",
                "conditions": {
                    "type": "threshold",
                    "metric": "brightness_change",
                    "operator": ">",
                    "value": 80,
                },
                "severity": "critical",
                "actions": ["webhook"],
            },
            {
                "name": "unusual_activity",
                "description": "Triggers when excessive motion events occur in a short window",
                "conditions": {
                    "type": "temporal",
                    "metric": "motion_events",
                    "min_occurrences": 5,
                    "window": 60,
                },
                "severity": "high",
                "actions": ["webhook"],
            },
        ]

    # ------------------------------------------------------------------
    # Dashboard configuration
    # ------------------------------------------------------------------

    @staticmethod
    def get_dashboard_config() -> dict:
        """Return default dashboard layout and KPI configuration."""
        return {
            "widgets": [
                {"type": "live_feed_grid", "layout": "2x2"},
                {"type": "incident_queue"},
                {"type": "zone_map"},
                {"type": "alert_history_chart"},
            ],
            "kpis": ["response_time", "false_alarm_rate", "coverage_pct"],
        }

    # ------------------------------------------------------------------
    # Report templates
    # ------------------------------------------------------------------

    @staticmethod
    def get_report_templates() -> list[str]:
        """Return available report template names."""
        return [
            "daily_security_summary",
            "incident_report",
            "weekly_analytics",
            "compliance_audit",
        ]

    # ------------------------------------------------------------------
    # Model / detection configuration
    # ------------------------------------------------------------------

    @staticmethod
    def get_model_configs() -> dict:
        """Return tuned model configurations for security use-cases."""
        return {
            "object_detection": {
                "model": "yolov8n",
                "confidence": 0.6,
                "classes": ["person", "vehicle", "backpack", "knife"],
            },
            "anomaly": {
                "sensitivity": "high",
            },
        }
