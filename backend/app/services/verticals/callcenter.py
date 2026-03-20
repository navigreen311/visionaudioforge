"""Call Center & QA vertical pack for automated call quality analysis."""

from __future__ import annotations

from typing import Any


class CallCenterVerticalPack:
    """Vertical pack providing call-centre pipelines, alerts, dashboards, and rubrics."""

    PACK_INFO: dict[str, str] = {
        "name": "Call Center & QA",
        "version": "1.0",
        "description": (
            "Automated call quality analysis, agent performance scoring, "
            "and compliance monitoring"
        ),
    }

    # ------------------------------------------------------------------
    # Pipeline templates
    # ------------------------------------------------------------------

    @staticmethod
    def get_pipeline_templates() -> dict[str, list[dict[str, Any]]]:
        """Return the five standard call-centre pipeline templates."""
        return {
            "call_quality_analysis": [
                {"step": "InputAudio"},
                {"step": "Transcribe"},
                {"step": "Diarize"},
                {"step": "SentimentPerSpeaker"},
                {"step": "QualityScore"},
                {"step": "Report"},
            ],
            "compliance_monitoring": [
                {"step": "InputAudio"},
                {"step": "Transcribe"},
                {
                    "step": "KeywordSpot",
                    "params": {
                        "keywords": ["guarantee", "promise", "refund", "legal"],
                    },
                },
                {"step": "ComplianceCheck"},
                {"step": "Alert", "params": {"condition": "if_violation"}},
            ],
            "agent_coaching": [
                {"step": "InputAudio"},
                {"step": "Transcribe"},
                {"step": "Diarize"},
                {"step": "TalkRatio"},
                {"step": "SentimentAnalysis"},
                {"step": "CoachingReport"},
            ],
            "customer_satisfaction": [
                {"step": "InputAudio"},
                {"step": "Transcribe"},
                {"step": "SentimentAnalysis"},
                {"step": "CSATScore"},
                {"step": "Dashboard"},
            ],
            "escalation_detection": [
                {"step": "InputAudio"},
                {"step": "Transcribe"},
                {"step": "SentimentPerSpeaker"},
                {
                    "step": "EscalationDetect",
                    "params": {"negative_threshold": 0.7},
                },
                {"step": "Alert"},
                {"step": "NotifyManager"},
            ],
        }

    # ------------------------------------------------------------------
    # Alert presets
    # ------------------------------------------------------------------

    @staticmethod
    def get_alert_presets() -> list[dict[str, str]]:
        """Return pre-configured alert definitions."""
        return [
            {
                "name": "compliance_violation",
                "severity": "critical",
            },
            {
                "name": "negative_sentiment_spike",
                "severity": "high",
            },
            {
                "name": "long_hold_time",
                "severity": "medium",
            },
            {
                "name": "agent_talk_ratio_high",
                "severity": "low",
            },
        ]

    # ------------------------------------------------------------------
    # Dashboard config
    # ------------------------------------------------------------------

    @staticmethod
    def get_dashboard_config() -> dict[str, Any]:
        """Return the default dashboard widget layout."""
        return {
            "widgets": [
                {"type": "chart", "name": "call_volume", "label": "Call Volume"},
                {"type": "metric", "name": "avg_handle_time", "label": "Avg Handle Time"},
                {"type": "metric", "name": "csat_score", "label": "CSAT Score"},
                {"type": "leaderboard", "name": "agent_leaderboard", "label": "Agent Leaderboard"},
                {"type": "metric", "name": "compliance_rate", "label": "Compliance Rate"},
            ],
        }

    # ------------------------------------------------------------------
    # Report templates
    # ------------------------------------------------------------------

    @staticmethod
    def get_report_templates() -> list[str]:
        """Return available report template names."""
        return [
            "agent_scorecard",
            "daily_call_summary",
            "compliance_report",
            "coaching_report",
        ]

    # ------------------------------------------------------------------
    # Quality rubric
    # ------------------------------------------------------------------

    @staticmethod
    def get_quality_rubric() -> dict[str, Any]:
        """Return the default quality-scoring rubric (weights sum to 1.0)."""
        return {
            "categories": [
                {
                    "name": "greeting",
                    "weight": 0.1,
                    "criteria": "Agent greets customer by name",
                },
                {
                    "name": "problem_identification",
                    "weight": 0.2,
                    "criteria": "Correctly identifies customer issue",
                },
                {
                    "name": "resolution",
                    "weight": 0.3,
                    "criteria": "Provides complete solution",
                },
                {
                    "name": "compliance",
                    "weight": 0.2,
                    "criteria": "Follows required disclosures",
                },
                {
                    "name": "closing",
                    "weight": 0.1,
                    "criteria": "Professional closing",
                },
                {
                    "name": "tone",
                    "weight": 0.1,
                    "criteria": "Maintains positive tone throughout",
                },
            ],
        }
