"""Call Center & QA vertical starter pack.

As with the other packs, the ``get_*`` classmethods are the pack's own
catalogue and the generic VerticalPack methods are derived from it, so the two
cannot drift apart.

This pack's catalogue describes pipelines as ordered *step* lists rather than
node/edge graphs, because that is how call handling is specified — a call is
processed front to back, not as a branching graph. ``pipelines()`` converts
each step list into the linear graph the generic installer expects.
"""

from __future__ import annotations

from typing import Any

from app.services.verticals.base import VerticalPack


class CallCenterVerticalPack(VerticalPack):
    """Pre-built call analysis pipelines, alerts and a QA scoring rubric."""

    PACK_INFO: dict[str, Any] = {
        "name": "Call Center & QA",
        "slug": "callcenter",
        "version": "1.0",
        "icon": "headset",
        "category": "Customer Service",
        "description": (
            "Call transcription, speaker diarisation and quality analysis, with "
            "compliance keyword spotting, escalation detection and agent coaching."
        ),
    }

    # ------------------------------------------------------------------
    # Pack catalogue
    # ------------------------------------------------------------------

    @classmethod
    def get_pipeline_templates(cls) -> dict[str, list[dict[str, Any]]]:
        """Call-processing pipelines, each an ordered list of steps."""
        return {
            "call_quality_analysis": [
                {"step": "InputAudio", "params": {"format": "wav"}},
                {"step": "Transcribe", "params": {"language": "en"}},
                {"step": "Diarize", "params": {"max_speakers": 2}},
                {"step": "SentimentPerSpeaker", "params": {}},
                {"step": "QualityScore", "params": {"rubric": "default"}},
                {"step": "Report", "params": {"template": "agent_scorecard"}},
            ],
            "compliance_monitoring": [
                {"step": "InputAudio", "params": {"format": "wav"}},
                {"step": "Transcribe", "params": {"language": "en"}},
                {
                    "step": "KeywordSpot",
                    # Words that commit the business to something it may not be
                    # able to honour, so a compliance reviewer should hear the call.
                    "params": {
                        "keywords": ["guarantee", "promise", "refund", "lawsuit", "cancel"],
                    },
                },
                {"step": "Alert", "params": {"preset": "compliance_violation"}},
            ],
            "agent_coaching": [
                {"step": "InputAudio", "params": {"format": "wav"}},
                {"step": "Transcribe", "params": {"language": "en"}},
                {"step": "QualityScore", "params": {"rubric": "default"}},
                {"step": "CoachingReport", "params": {"window": "weekly"}},
            ],
            "customer_satisfaction": [
                {"step": "InputAudio", "params": {"format": "wav"}},
                {"step": "Transcribe", "params": {"language": "en"}},
                {"step": "SentimentPerSpeaker", "params": {}},
                {"step": "CsatEstimate", "params": {"scale": 5}},
            ],
            "escalation_detection": [
                {"step": "InputAudio", "params": {"format": "wav"}},
                {"step": "Transcribe", "params": {"language": "en"}},
                {"step": "SentimentPerSpeaker", "params": {}},
                {"step": "EscalationDetect", "params": {"negative_threshold": 0.7}},
                {"step": "Alert", "params": {"preset": "negative_sentiment_spike"}},
            ],
        }

    @classmethod
    def get_alert_presets(cls) -> list[dict[str, Any]]:
        """Alert rules installed with the pack."""
        return [
            {
                "name": "compliance_violation",
                "title": "Compliance Violation",
                "severity": "critical",
                "conditions": {"keyword_hit": True},
                "cooldown_seconds": 0,
            },
            {
                "name": "negative_sentiment_spike",
                "title": "Negative Sentiment Spike",
                "severity": "high",
                "conditions": {"negative_sentiment": {">": 0.7}},
                "cooldown_seconds": 60,
            },
            {
                "name": "long_hold_time",
                "title": "Long Hold Time",
                "severity": "medium",
                "conditions": {"hold_seconds": {">": 180}},
                "cooldown_seconds": 300,
            },
            {
                "name": "agent_talk_ratio_high",
                "title": "Agent Talking Too Much",
                "severity": "low",
                "conditions": {"agent_talk_ratio": {">": 0.7}},
                "cooldown_seconds": 600,
            },
        ]

    @classmethod
    def get_dashboard_config(cls) -> dict[str, Any]:
        """Widget layout installed for call centre supervisors."""
        return {
            "widgets": [
                {"name": "call_volume", "type": "chart", "title": "Call Volume", "metric": "calls_total"},
                {"name": "avg_handle_time", "type": "stat", "title": "Avg Handle Time", "metric": "aht_seconds"},
                {"name": "csat_score", "type": "gauge", "title": "CSAT", "metric": "csat_estimate"},
                {"name": "agent_leaderboard", "type": "table", "title": "Agent Leaderboard", "metric": "agent_scores"},
                {"name": "compliance_rate", "type": "gauge", "title": "Compliance Rate", "metric": "compliance_rate"},
            ],
        }

    @classmethod
    def get_report_templates(cls) -> dict[str, dict[str, Any]]:
        """Scheduled reports installed with the pack."""
        return {
            "agent_scorecard": {"name": "Agent Scorecard", "schedule": "weekly"},
            "daily_call_summary": {"name": "Daily Call Summary", "schedule": "daily"},
            "compliance_report": {"name": "Compliance Report", "schedule": "monthly"},
            "coaching_report": {"name": "Coaching Report", "schedule": "weekly"},
        }

    @classmethod
    def get_quality_rubric(cls) -> dict[str, Any]:
        """The QA rubric CallScoringService scores calls against.

        Weights sum to 1.0 so an overall score is a straight weighted mean;
        changing one weight means changing another.
        """
        return {
            "name": "Default Call Quality Rubric",
            "categories": [
                {
                    "name": "greeting",
                    "weight": 0.15,
                    "criteria": "Agent opens with a greeting and identifies themselves.",
                    "keywords": ["hello", "welcome", "my name is", "thank you for calling"],
                },
                {
                    "name": "empathy",
                    "weight": 0.20,
                    "criteria": "Agent acknowledges the customer's problem and shows understanding.",
                    "keywords": ["understand", "sorry", "apologise", "apologize", "help"],
                },
                {
                    "name": "resolution",
                    "weight": 0.30,
                    "criteria": "Agent resolves the issue or states a concrete next step.",
                    "keywords": ["solution", "resolve", "fixed", "done", "next step"],
                },
                {
                    "name": "compliance",
                    "weight": 0.20,
                    "criteria": "Agent gives required disclosures and avoids prohibited claims.",
                    "keywords": ["policy", "disclosure", "terms", "recorded"],
                },
                {
                    "name": "tone",
                    "weight": 0.15,
                    "criteria": "Agent maintains a positive, professional tone throughout.",
                    "keywords": ["great", "happy", "certainly", "of course"],
                },
            ],
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
        """Convert each step list into the linear node/edge graph installers use."""
        result: dict[str, dict[str, Any]] = {}

        for slug, steps in self.get_pipeline_templates().items():
            nodes = [
                {
                    "id": f"step_{index + 1}",
                    "type": _step_to_node_type(step["step"]),
                    "params": step.get("params", {}),
                }
                for index, step in enumerate(steps)
            ]
            edges = [
                {
                    "from": nodes[i]["id"],
                    "to": nodes[i + 1]["id"],
                    "from_port": "output",
                    "to_port": "input",
                }
                for i in range(len(nodes) - 1)
            ]
            result[slug] = {
                "name": slug.replace("_", " ").title(),
                "description": f"Call centre pipeline: {slug.replace('_', ' ')}.",
                "nodes": nodes,
                "edges": edges,
            }

        return result

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        """Key the catalogue's alert list by name for the generic interface."""
        return {
            preset["name"]: {
                "name": preset.get("title", preset["name"]),
                "severity": preset["severity"],
                "conditions": preset["conditions"],
                "cooldown_seconds": preset.get("cooldown_seconds", 0),
            }
            for preset in self.get_alert_presets()
        }

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        return self.get_dashboard_config()["widgets"]

    def reports(self) -> dict[str, dict[str, Any]]:
        return self.get_report_templates()


def _step_to_node_type(step: str) -> str:
    """Map a catalogue step name onto a pipeline node type (CamelCase -> snake)."""
    out: list[str] = []
    for index, char in enumerate(step):
        if char.isupper() and index:
            out.append("_")
        out.append(char.lower())
    return "".join(out)
