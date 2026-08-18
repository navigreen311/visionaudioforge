"""Healthcare & Clinical vertical starter pack.

Two APIs are exposed over one body of data, deliberately:

* ``PACK_INFO`` and the ``get_*`` classmethods are the pack's own catalogue —
  what a clinical deployment installs, including the HIPAA configuration and
  model settings that have no equivalent in the generic pack interface.
* ``info()`` / ``pipelines()`` / ``alert_presets()`` / ``dashboard_widgets()`` /
  ``reports()`` are the generic VerticalPack interface the installer and the
  /api/verticals routes consume.

The second is derived from the first rather than written out twice. The two
drifting apart is what left this pack advertising two pipelines while its
specification described five.
"""

from __future__ import annotations

from typing import Any

from app.services.verticals.base import VerticalPack


class HealthcareVerticalPack(VerticalPack):
    """Pre-built pipelines, alerts and compliance settings for clinical sites."""

    PACK_INFO: dict[str, Any] = {
        "name": "Healthcare & Clinical",
        "slug": "healthcare",
        "version": "1.0",
        "icon": "heart-pulse",
        "category": "Healthcare",
        "description": (
            "Patient monitoring, medical imaging support, clinical documentation "
            "and medication verification, with HIPAA-aligned retention, audit and "
            "PHI redaction defaults."
        ),
    }

    # ------------------------------------------------------------------
    # Pack catalogue
    # ------------------------------------------------------------------

    @classmethod
    def get_pipeline_templates(cls) -> dict[str, dict[str, Any]]:
        """Ready-to-install pipeline definitions for clinical workflows."""
        return {
            "patient_monitoring": {
                "name": "Patient Monitoring",
                "category": "Healthcare",
                "description": "Watch a room for falls and abnormal movement, and alert staff.",
                "definition": {
                    "nodes": [
                        {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 30}},
                        {"id": "flow_1", "type": "optical_flow", "params": {"method": "farneback"}},
                        {"id": "fall_1", "type": "fall_detection", "params": {"sensitivity": "high"}},
                        {"id": "alert_1", "type": "alert", "params": {"preset": "patient_fall"}},
                    ],
                    "edges": [
                        {"from": "input_1", "to": "flow_1", "from_port": "output", "to_port": "input"},
                        {"from": "flow_1", "to": "fall_1", "from_port": "output", "to_port": "input"},
                        {"from": "fall_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                    ],
                },
            },
            "medical_image_analysis": {
                "name": "Medical Image Analysis",
                "category": "Healthcare",
                "description": "Run a classifier over clinical imagery and record findings.",
                "definition": {
                    "nodes": [
                        {"id": "input_1", "type": "input_image", "params": {"path": ""}},
                        {"id": "pre_1", "type": "preprocess", "params": {"normalize": "zscore"}},
                        {"id": "classify_1", "type": "classify", "params": {"model": "clinical-imaging-v1"}},
                        {"id": "save_1", "type": "save_asset", "params": {"filename": "findings.json", "format": "json"}},
                    ],
                    "edges": [
                        {"from": "input_1", "to": "pre_1", "from_port": "output", "to_port": "input"},
                        {"from": "pre_1", "to": "classify_1", "from_port": "output", "to_port": "input"},
                        {"from": "classify_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                    ],
                },
            },
            "clinical_documentation": {
                "name": "Clinical Documentation",
                "category": "Healthcare",
                "description": "Transcribe dictated notes and strip identifiers before storage.",
                "definition": {
                    "nodes": [
                        {"id": "input_1", "type": "input_audio", "params": {"path": ""}},
                        {"id": "stt_1", "type": "transcribe", "params": {"language": "en"}},
                        {"id": "deid_1", "type": "deidentify", "params": {"mode": "strict"}},
                        {"id": "save_1", "type": "save_asset", "params": {"filename": "note.txt", "format": "text"}},
                    ],
                    "edges": [
                        {"from": "input_1", "to": "stt_1", "from_port": "output", "to_port": "input"},
                        {"from": "stt_1", "to": "deid_1", "from_port": "output", "to_port": "input"},
                        {"from": "deid_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                    ],
                },
            },
            "medication_verification": {
                "name": "Medication Verification",
                "category": "Healthcare",
                "description": "Read a medication label and check it against the order.",
                "definition": {
                    "nodes": [
                        {"id": "input_1", "type": "input_image", "params": {"path": ""}},
                        {"id": "ocr_1", "type": "ocr", "params": {"language": "en"}},
                        {"id": "match_1", "type": "filter", "params": {"condition": "matches_order"}},
                        {"id": "alert_1", "type": "alert", "params": {"preset": "medication_error"}},
                    ],
                    "edges": [
                        {"from": "input_1", "to": "ocr_1", "from_port": "output", "to_port": "input"},
                        {"from": "ocr_1", "to": "match_1", "from_port": "output", "to_port": "input"},
                        {"from": "match_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                    ],
                },
            },
            "wound_assessment": {
                "name": "Wound Assessment",
                "category": "Healthcare",
                "description": "Measure wound area over time from serial photographs.",
                "definition": {
                    "nodes": [
                        {"id": "input_1", "type": "input_image", "params": {"path": ""}},
                        {"id": "segment_1", "type": "segment", "params": {"model": "wound-seg-v1"}},
                        {"id": "measure_1", "type": "measure", "params": {"unit": "cm2"}},
                        {"id": "save_1", "type": "save_asset", "params": {"filename": "wound.json", "format": "json"}},
                    ],
                    "edges": [
                        {"from": "input_1", "to": "segment_1", "from_port": "output", "to_port": "input"},
                        {"from": "segment_1", "to": "measure_1", "from_port": "output", "to_port": "input"},
                        {"from": "measure_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                    ],
                },
            },
        }

    @classmethod
    def get_compliance_config(cls) -> dict[str, Any]:
        """HIPAA defaults applied when this pack is installed.

        Six years is the HIPAA minimum retention for documentation; state law
        can require longer, so this is a floor rather than a recommendation.
        """
        return {
            "standard": "HIPAA",
            "encrypt_at_rest": True,
            "encrypt_in_transit": True,
            "audit_all_access": True,
            "auto_pii_redaction": True,
            "data_retention_years": 6,
            "minimum_necessary": True,
            "breach_notification_days": 60,
        }

    @classmethod
    def get_alert_presets(cls) -> dict[str, dict[str, Any]]:
        """Alert rules installed with the pack."""
        return {
            "patient_fall": {
                "name": "Patient Fall",
                "severity": "critical",
                "conditions": {"motion_magnitude": {">": 0.7}, "direction": "downward"},
                "cooldown_seconds": 15,
            },
            "abnormal_vital_pattern": {
                "name": "Abnormal Vital Pattern",
                "severity": "high",
                "conditions": {"anomaly_score": {">": 0.8}},
                "cooldown_seconds": 60,
            },
            "medication_error": {
                "name": "Medication Mismatch",
                "severity": "critical",
                "conditions": {"label_matches_order": False},
                "cooldown_seconds": 0,
            },
            "unauthorized_access_to_records": {
                "name": "Unauthorized Record Access",
                "severity": "high",
                "conditions": {"access_granted": False, "resource_type": "patient_record"},
                "cooldown_seconds": 0,
            },
        }

    @classmethod
    def get_dashboard_config(cls) -> dict[str, Any]:
        """Widget layout installed for clinical operators."""
        return {
            "widgets": [
                {"id": "patient_status", "type": "stat", "title": "Patients Monitored", "metric": "patients_monitored"},
                {"id": "active_monitors", "type": "stat", "title": "Active Monitors", "metric": "active_streams"},
                {"id": "alert_queue", "type": "list", "title": "Open Alerts", "metric": "open_alerts"},
                {"id": "compliance_status", "type": "gauge", "title": "Compliance Status", "metric": "compliance_score"},
            ],
        }

    @classmethod
    def get_report_templates(cls) -> dict[str, dict[str, Any]]:
        """Scheduled reports installed with the pack."""
        return {
            "patient_incident_report": {"name": "Patient Incident Report", "schedule": "on_demand"},
            "daily_ward_summary": {"name": "Daily Ward Summary", "schedule": "daily"},
            "compliance_audit": {"name": "Compliance Audit", "schedule": "monthly"},
            "clinical_study_export": {"name": "Clinical Study Export", "schedule": "on_demand"},
        }

    @classmethod
    def get_model_configs(cls) -> dict[str, dict[str, Any]]:
        """Model settings tuned for clinical risk tolerance.

        Both lean towards false positives: a missed fall or a leaked identifier
        costs more than a nurse dismissing an alert.
        """
        return {
            "anomaly_detection": {"sensitivity": "high", "threshold": 0.8},
            "pii_scanner": {"mode": "strict", "redact": True},
        }

    # ------------------------------------------------------------------
    # Generic VerticalPack interface — derived from the catalogue above
    # ------------------------------------------------------------------

    def info(self) -> dict[str, Any]:
        return {
            "name": self.PACK_INFO["name"],
            "slug": self.PACK_INFO["slug"],
            "icon": self.PACK_INFO["icon"],
            "description": self.PACK_INFO["description"],
            "category": self.PACK_INFO["category"],
        }

    def pipelines(self) -> dict[str, dict[str, Any]]:
        return {
            slug: {
                "name": tmpl["name"],
                "description": tmpl.get("description", ""),
                **tmpl["definition"],
            }
            for slug, tmpl in self.get_pipeline_templates().items()
        }

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        return self.get_alert_presets()

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        return self.get_dashboard_config()["widgets"]

    def reports(self) -> dict[str, dict[str, Any]]:
        return self.get_report_templates()
