"""Education vertical starter pack."""

from __future__ import annotations

from typing import Any

from app.services.verticals.base import VerticalPack


class EducationVerticalPack(VerticalPack):
    """Pre-built pipelines and alerts for education deployments.

    Covers lecture analysis, student engagement monitoring, lab safety,
    and content accessibility (captioning).
    """

    def info(self) -> dict[str, Any]:
        return {
            "name": "Education",
            "slug": "education",
            "icon": "graduation-cap",
            "description": (
                "Lecture transcription and summarization, engagement monitoring, "
                "lab safety detection, and accessibility captioning for educational institutions."
            ),
            "category": "Education",
        }

    # ------------------------------------------------------------------
    # Pipelines
    # ------------------------------------------------------------------

    def pipelines(self) -> dict[str, dict[str, Any]]:
        return {
            "lecture_analysis": {
                "name": "Lecture Analysis",
                "description": "Transcribe lecture audio, summarize, and extract key concepts.",
                "nodes": [
                    {"id": "input_1", "type": "input_audio", "params": {"path": ""}},
                    {"id": "mfcc_1", "type": "mfcc", "params": {"n_mfcc": 13}},
                    {"id": "mel_1", "type": "mel_spectrogram", "params": {"n_mels": 80}},
                    {"id": "log_1", "type": "log", "params": {"label": "lecture_concepts"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "lecture_summary.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "mfcc_1", "from_port": "output", "to_port": "input"},
                    {"from": "mfcc_1", "to": "mel_1", "from_port": "output", "to_port": "input"},
                    {"from": "mel_1", "to": "log_1", "from_port": "output", "to_port": "input"},
                    {"from": "log_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "engagement_monitoring": {
                "name": "Engagement Monitoring",
                "description": "Detect faces in classroom video, estimate attention levels, and report.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 30}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.4}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 0.3}},
                    {"id": "log_1", "type": "log", "params": {"label": "engagement_score"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "engagement_report.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "log_1", "from_port": "output", "to_port": "input"},
                    {"from": "log_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "lab_safety": {
                "name": "Lab Safety",
                "description": "Detect unsafe behaviour in laboratory video and raise alerts.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 15}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.5}},
                    {"id": "cond_1", "type": "conditional", "params": {"condition": "unsafe_behavior"}},
                    {"id": "alert_1", "type": "alert", "params": {"message": "Unsafe lab behaviour detected", "severity": "critical"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "lab_safety_log.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "cond_1", "from_port": "output", "to_port": "input"},
                    {"from": "cond_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                    {"from": "alert_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "content_accessibility": {
                "name": "Content Accessibility",
                "description": "Transcribe audio content and generate captions for accessibility compliance.",
                "nodes": [
                    {"id": "input_1", "type": "input_audio", "params": {"path": ""}},
                    {"id": "mfcc_1", "type": "mfcc", "params": {"n_mfcc": 13}},
                    {"id": "mel_1", "type": "mel_spectrogram", "params": {"n_mels": 80}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "captions.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "mfcc_1", "from_port": "output", "to_port": "input"},
                    {"from": "mfcc_1", "to": "mel_1", "from_port": "output", "to_port": "input"},
                    {"from": "mel_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
        }

    # ------------------------------------------------------------------
    # Alert presets
    # ------------------------------------------------------------------

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        return {
            "low_engagement": {
                "name": "Low Engagement",
                "severity": "warning",
                "conditions": {"engagement_score": {"<": 0.3}},
                "cooldown_seconds": 300,
            },
            "lab_safety_violation": {
                "name": "Lab Safety Violation",
                "severity": "critical",
                "conditions": {"unsafe_behavior_detected": True},
                "cooldown_seconds": 15,
            },
            "accessibility_gap": {
                "name": "Accessibility Gap",
                "severity": "medium",
                "conditions": {"caption_coverage_pct": {"<": 95}},
                "cooldown_seconds": 3600,
            },
        }

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        return [
            {"type": "chart", "title": "Class Analytics", "metric": "lecture_count_trend"},
            {"type": "gauge", "title": "Engagement Scores", "metric": "avg_engagement"},
            {"type": "stat", "title": "Safety Incidents", "metric": "safety_incident_count"},
            {"type": "stat", "title": "Accessibility Coverage", "metric": "caption_coverage_pct"},
        ]

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def reports(self) -> dict[str, dict[str, Any]]:
        return {
            "weekly_class_report": {
                "name": "Weekly Class Report",
                "schedule": "weekly",
                "sections": ["lecture_count", "avg_engagement", "key_topics"],
            },
            "safety_incident_log": {
                "name": "Safety Incident Log",
                "schedule": "daily",
                "sections": ["incidents", "severity_breakdown", "response_time"],
            },
            "accessibility_audit": {
                "name": "Accessibility Audit",
                "schedule": "monthly",
                "sections": ["caption_coverage", "compliance_gaps", "remediation_plan"],
            },
        }
