"""Healthcare & Clinical vertical pack.

Provides HIPAA-compliant pipeline templates, alert presets, compliance
configuration, dashboard widgets, report templates, and model configs
tuned for clinical imaging, patient monitoring, and medical documentation.
"""

from __future__ import annotations

from typing import Any


def _build_definition(node_specs: list[tuple[str, str, dict[str, Any]]]) -> dict[str, Any]:
    """Build a valid pipeline definition from a list of (id, type, params) tuples."""
    nodes = [{"id": nid, "type": ntype, "params": params} for nid, ntype, params in node_specs]
    edges = [
        {
            "from": node_specs[i][0],
            "to": node_specs[i + 1][0],
            "from_port": "output",
            "to_port": "input",
        }
        for i in range(len(node_specs) - 1)
    ]
    return {"nodes": nodes, "edges": edges}


class HealthcareVerticalPack:
    """Healthcare & Clinical vertical pack with HIPAA-compliant pipelines."""

    PACK_INFO: dict[str, str] = {
        "name": "Healthcare & Clinical",
        "version": "1.0",
        "description": (
            "HIPAA-compliant pipelines for clinical imaging, patient monitoring, "
            "and medical documentation"
        ),
    }

    # ------------------------------------------------------------------
    # Pipeline templates
    # ------------------------------------------------------------------

    @staticmethod
    def get_pipeline_templates() -> dict[str, dict[str, Any]]:
        """Return healthcare-specific pipeline templates."""
        return {
            "patient_monitoring": {
                "name": "Patient Monitoring",
                "description": "Real-time patient fall detection via pose estimation.",
                "category": "Healthcare",
                "definition": _build_definition([
                    ("input_1", "input_video", {"path": ""}),
                    ("detect_1", "detect_objects", {"class": "person"}),
                    ("pose_1", "pose_estimate", {}),
                    ("fall_1", "fall_detection", {"angle_threshold": 45}),
                    ("alert_1", "alert", {"severity": "critical"}),
                ]),
            },
            "medical_image_analysis": {
                "name": "Medical Image Analysis",
                "description": "Normalize, enhance, and detect anomalies in medical images.",
                "category": "Healthcare",
                "definition": _build_definition([
                    ("input_1", "input_image", {"path": ""}),
                    ("normalize_1", "normalize", {"method": "z_score"}),
                    ("enhance_1", "enhance", {"type": "contrast"}),
                    ("anomaly_1", "detect_anomalies", {}),
                    ("report_1", "report", {}),
                ]),
            },
            "clinical_documentation": {
                "name": "Clinical Documentation",
                "description": "Transcribe audio, extract medical terms, and summarize clinical notes.",
                "category": "Healthcare",
                "definition": _build_definition([
                    ("input_1", "input_audio", {"path": ""}),
                    ("transcribe_1", "transcribe", {}),
                    ("extract_1", "extract_medical_terms", {}),
                    ("summarize_1", "summarize_note", {}),
                    ("output_1", "output", {}),
                ]),
            },
            "medication_verification": {
                "name": "Medication Verification",
                "description": "OCR medication labels and verify against prescriptions.",
                "category": "Healthcare",
                "definition": _build_definition([
                    ("input_1", "input_image", {"path": ""}),
                    ("ocr_1", "ocr", {}),
                    ("extract_1", "extract_drug_name", {}),
                    ("verify_1", "verify_against_prescription", {}),
                    ("alert_1", "alert", {"condition": "if_mismatch"}),
                ]),
            },
            "wound_assessment": {
                "name": "Wound Assessment",
                "description": "Analyze wound images for color, area measurement, and progress tracking.",
                "category": "Healthcare",
                "definition": _build_definition([
                    ("input_1", "input_image", {"path": ""}),
                    ("normalize_1", "normalize", {"method": "min_max"}),
                    ("color_1", "color_analysis", {"mode": "skin_tone"}),
                    ("measure_1", "measure_area", {}),
                    ("track_1", "track_progress", {}),
                ]),
            },
        }

    # ------------------------------------------------------------------
    # Alert presets
    # ------------------------------------------------------------------

    @staticmethod
    def get_alert_presets() -> dict[str, dict[str, Any]]:
        """Return alert presets for healthcare scenarios."""
        return {
            "patient_fall": {
                "name": "Patient Fall",
                "severity": "critical",
                "description": "Triggered when fall detection identifies a patient fall event.",
                "auto_escalate": True,
            },
            "abnormal_vital_pattern": {
                "name": "Abnormal Vital Pattern",
                "severity": "high",
                "description": "Triggered when vital sign patterns deviate from expected baselines.",
                "auto_escalate": True,
            },
            "medication_error": {
                "name": "Medication Error",
                "severity": "critical",
                "description": "Triggered when medication verification detects a mismatch.",
                "auto_escalate": True,
            },
            "unauthorized_access_to_records": {
                "name": "Unauthorized Access to Records",
                "severity": "high",
                "description": "Triggered when access to patient records fails authorization checks.",
                "auto_escalate": True,
            },
        }

    # ------------------------------------------------------------------
    # Compliance configuration
    # ------------------------------------------------------------------

    @staticmethod
    def get_compliance_config() -> dict[str, Any]:
        """Return HIPAA-compliant configuration defaults."""
        return {
            "standard": "HIPAA",
            "encrypt_at_rest": True,
            "audit_all_access": True,
            "auto_pii_redaction": True,
            "data_retention_years": 6,
            "minimum_necessary": True,
        }

    # ------------------------------------------------------------------
    # Dashboard configuration
    # ------------------------------------------------------------------

    @staticmethod
    def get_dashboard_config() -> dict[str, Any]:
        """Return dashboard widget configuration for healthcare."""
        return {
            "widgets": [
                {
                    "id": "patient_status",
                    "type": "status_grid",
                    "title": "Patient Status",
                    "description": "Real-time overview of monitored patients.",
                    "refresh_interval_seconds": 5,
                },
                {
                    "id": "active_monitors",
                    "type": "counter",
                    "title": "Active Monitors",
                    "description": "Number of active monitoring pipelines.",
                    "refresh_interval_seconds": 10,
                },
                {
                    "id": "alert_queue",
                    "type": "list",
                    "title": "Alert Queue",
                    "description": "Pending alerts requiring clinical review.",
                    "refresh_interval_seconds": 5,
                },
                {
                    "id": "compliance_status",
                    "type": "indicator",
                    "title": "Compliance Status",
                    "description": "Current HIPAA compliance posture.",
                    "refresh_interval_seconds": 60,
                },
            ],
        }

    # ------------------------------------------------------------------
    # Report templates
    # ------------------------------------------------------------------

    @staticmethod
    def get_report_templates() -> dict[str, dict[str, Any]]:
        """Return report templates for clinical workflows."""
        return {
            "patient_incident_report": {
                "name": "Patient Incident Report",
                "description": "Detailed report for patient safety incidents.",
                "sections": ["incident_summary", "timeline", "actions_taken", "follow_up"],
            },
            "daily_ward_summary": {
                "name": "Daily Ward Summary",
                "description": "End-of-day summary of ward activity and alerts.",
                "sections": ["patient_count", "alerts_triggered", "resolved", "pending"],
            },
            "compliance_audit": {
                "name": "Compliance Audit",
                "description": "HIPAA compliance audit trail for a given period.",
                "sections": ["access_log", "pii_redactions", "data_retention", "violations"],
            },
            "clinical_study_export": {
                "name": "Clinical Study Export",
                "description": "De-identified data export for clinical studies.",
                "sections": ["methodology", "data_summary", "anonymization_log"],
            },
        }

    # ------------------------------------------------------------------
    # Model configurations
    # ------------------------------------------------------------------

    @staticmethod
    def get_model_configs() -> dict[str, dict[str, Any]]:
        """Return model configurations tuned for clinical use."""
        return {
            "anomaly_detection": {
                "name": "Clinical Anomaly Detection",
                "description": "High-sensitivity anomaly detection for medical imaging.",
                "sensitivity": "high",
                "confidence_threshold": 0.3,
                "false_negative_weight": 5.0,
                "modalities": ["xray", "ct", "mri", "ultrasound"],
            },
            "pii_scanner": {
                "name": "Strict PII Scanner",
                "description": "Aggressive PII detection for HIPAA compliance.",
                "mode": "strict",
                "entity_types": [
                    "patient_name",
                    "date_of_birth",
                    "mrn",
                    "ssn",
                    "address",
                    "phone",
                    "email",
                ],
                "redaction_style": "replace",
                "replacement_token": "[REDACTED]",
            },
        }
