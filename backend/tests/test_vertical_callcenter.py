"""Tests for the Call Center & QA vertical pack and scoring service."""

from __future__ import annotations

import math

import pytest

from app.services.verticals.callcenter import CallCenterVerticalPack
from app.services.verticals.call_scoring import CallScoringService


# ---------------------------------------------------------------
# CallCenterVerticalPack
# ---------------------------------------------------------------


class TestCallCenterVerticalPack:
    """Tests for pack metadata, pipelines, alerts, dashboards, reports, rubric."""

    def test_pack_info(self):
        assert CallCenterVerticalPack.PACK_INFO["name"] == "Call Center & QA"
        assert CallCenterVerticalPack.PACK_INFO["version"] == "1.0"
        assert "quality analysis" in CallCenterVerticalPack.PACK_INFO["description"]

    # -- Pipeline templates --

    def test_pipeline_templates_count(self):
        templates = CallCenterVerticalPack.get_pipeline_templates()
        assert len(templates) == 5

    def test_pipeline_template_names(self):
        templates = CallCenterVerticalPack.get_pipeline_templates()
        expected = {
            "call_quality_analysis",
            "compliance_monitoring",
            "agent_coaching",
            "customer_satisfaction",
            "escalation_detection",
        }
        assert set(templates.keys()) == expected

    def test_call_quality_pipeline_steps(self):
        pipeline = CallCenterVerticalPack.get_pipeline_templates()["call_quality_analysis"]
        steps = [s["step"] for s in pipeline]
        assert steps == [
            "InputAudio", "Transcribe", "Diarize",
            "SentimentPerSpeaker", "QualityScore", "Report",
        ]

    def test_compliance_pipeline_has_keyword_spot(self):
        pipeline = CallCenterVerticalPack.get_pipeline_templates()["compliance_monitoring"]
        keyword_step = next(s for s in pipeline if s["step"] == "KeywordSpot")
        assert "guarantee" in keyword_step["params"]["keywords"]

    def test_escalation_pipeline_threshold(self):
        pipeline = CallCenterVerticalPack.get_pipeline_templates()["escalation_detection"]
        esc_step = next(s for s in pipeline if s["step"] == "EscalationDetect")
        assert esc_step["params"]["negative_threshold"] == 0.7

    # -- Alert presets --

    def test_alert_presets_count(self):
        alerts = CallCenterVerticalPack.get_alert_presets()
        assert len(alerts) == 4

    def test_alert_presets_severities(self):
        alerts = CallCenterVerticalPack.get_alert_presets()
        severity_map = {a["name"]: a["severity"] for a in alerts}
        assert severity_map["compliance_violation"] == "critical"
        assert severity_map["negative_sentiment_spike"] == "high"
        assert severity_map["long_hold_time"] == "medium"
        assert severity_map["agent_talk_ratio_high"] == "low"

    # -- Dashboard config --

    def test_dashboard_widget_count(self):
        config = CallCenterVerticalPack.get_dashboard_config()
        assert len(config["widgets"]) == 5

    def test_dashboard_widget_names(self):
        config = CallCenterVerticalPack.get_dashboard_config()
        names = {w["name"] for w in config["widgets"]}
        expected = {
            "call_volume", "avg_handle_time", "csat_score",
            "agent_leaderboard", "compliance_rate",
        }
        assert names == expected

    # -- Report templates --

    def test_report_templates(self):
        templates = CallCenterVerticalPack.get_report_templates()
        assert "agent_scorecard" in templates
        assert "daily_call_summary" in templates
        assert "compliance_report" in templates
        assert "coaching_report" in templates

    # -- Quality rubric --

    def test_quality_rubric_categories(self):
        rubric = CallCenterVerticalPack.get_quality_rubric()
        names = [c["name"] for c in rubric["categories"]]
        assert "greeting" in names
        assert "resolution" in names
        assert "tone" in names

    def test_quality_rubric_weights_sum_to_one(self):
        rubric = CallCenterVerticalPack.get_quality_rubric()
        total = sum(c["weight"] for c in rubric["categories"])
        assert math.isclose(total, 1.0, abs_tol=1e-9)

    def test_quality_rubric_has_criteria(self):
        rubric = CallCenterVerticalPack.get_quality_rubric()
        for cat in rubric["categories"]:
            assert "criteria" in cat
            assert isinstance(cat["criteria"], str)
            assert len(cat["criteria"]) > 0


# ---------------------------------------------------------------
# CallScoringService
# ---------------------------------------------------------------


class TestCallScoringService:
    """Tests for call scoring, coaching reports, and CSAT estimation."""

    @pytest.fixture()
    def rubric(self):
        return CallCenterVerticalPack.get_quality_rubric()

    @pytest.fixture()
    def good_transcript(self):
        return [
            {"text": "Hello, welcome! My name is Alex.", "sentiment": 0.8},
            {"text": "I understand your issue, let me help.", "sentiment": 0.5},
            {"text": "The solution is to reset your account.", "sentiment": 0.4},
            {"text": "Per our policy disclosure, here are the terms.", "sentiment": 0.3},
            {"text": "Thank you, have a great day! Goodbye.", "sentiment": 0.9},
        ]

    @pytest.fixture()
    def poor_transcript(self):
        return [
            {"text": "Yeah what do you want.", "sentiment": -0.5},
            {"text": "I dunno.", "sentiment": -0.6},
        ]

    # -- score_call --

    def test_score_call_returns_required_keys(self, rubric, good_transcript):
        result = CallScoringService.score_call(good_transcript, rubric)
        assert "overall_score" in result
        assert "category_scores" in result
        assert "highlights" in result
        assert "improvements" in result

    def test_score_call_overall_range(self, rubric, good_transcript):
        result = CallScoringService.score_call(good_transcript, rubric)
        assert 0 <= result["overall_score"] <= 100

    def test_score_call_good_beats_poor(self, rubric, good_transcript, poor_transcript):
        good_score = CallScoringService.score_call(good_transcript, rubric)["overall_score"]
        poor_score = CallScoringService.score_call(poor_transcript, rubric)["overall_score"]
        assert good_score > poor_score

    def test_score_call_category_scores_present(self, rubric, good_transcript):
        result = CallScoringService.score_call(good_transcript, rubric)
        for cat in rubric["categories"]:
            assert cat["name"] in result["category_scores"]

    def test_score_call_empty_transcript(self, rubric):
        result = CallScoringService.score_call([], rubric)
        assert 0 <= result["overall_score"] <= 100

    # -- generate_coaching_report --

    def test_coaching_report_structure(self, rubric, good_transcript):
        scores = [CallScoringService.score_call(good_transcript, rubric) for _ in range(5)]
        report = CallScoringService.generate_coaching_report(scores, "agent-42")
        assert report["agent_id"] == "agent-42"
        assert isinstance(report["period_avg_score"], float)
        assert report["trend"] in ("improving", "declining", "stable")
        assert isinstance(report["strengths"], list)
        assert isinstance(report["areas_for_improvement"], list)
        assert isinstance(report["recommended_training"], list)

    def test_coaching_report_empty_scores(self):
        report = CallScoringService.generate_coaching_report([], "agent-0")
        assert report["agent_id"] == "agent-0"
        assert report["period_avg_score"] == 0.0
        assert report["trend"] == "insufficient_data"

    def test_coaching_report_trend_improving(self, rubric):
        # Simulate improving scores
        low_segments = [{"text": "um", "sentiment": -0.3}]
        high_segments = [
            {"text": "Hello welcome, I understand your issue. Solution done. Thank you goodbye.", "sentiment": 0.8},
        ]
        scores = (
            [CallScoringService.score_call(low_segments, rubric) for _ in range(5)]
            + [CallScoringService.score_call(high_segments, rubric) for _ in range(5)]
        )
        report = CallScoringService.generate_coaching_report(scores, "agent-x")
        assert report["trend"] == "improving"

    # -- compute_csat_estimate --

    def test_csat_very_positive(self):
        csat = CallScoringService.compute_csat_estimate([0.8, 0.9, 0.7])
        assert csat == 5.0

    def test_csat_very_negative(self):
        csat = CallScoringService.compute_csat_estimate([-0.8, -0.9, -0.7])
        assert csat == 1.0

    def test_csat_neutral(self):
        csat = CallScoringService.compute_csat_estimate([0.0, 0.1, -0.1])
        assert csat == 3.0

    def test_csat_mixed(self):
        csat = CallScoringService.compute_csat_estimate([0.8, -0.8])
        assert csat == 3.0  # (5 + 1) / 2

    def test_csat_empty(self):
        csat = CallScoringService.compute_csat_estimate([])
        assert csat == 3.0

    def test_csat_range(self):
        csat = CallScoringService.compute_csat_estimate([0.3, -0.3, 0.0])
        assert 1.0 <= csat <= 5.0


# ---------------------------------------------------------------
# API / Install smoke test
# ---------------------------------------------------------------


class TestVerticalPackInstall:
    """Verify the pack can be imported and instantiated."""

    def test_pack_instantiation(self):
        pack = CallCenterVerticalPack()
        assert pack.PACK_INFO["name"] == "Call Center & QA"

    def test_scoring_service_instantiation(self):
        svc = CallScoringService()
        assert callable(svc.score_call)
        assert callable(svc.generate_coaching_report)
        assert callable(svc.compute_csat_estimate)

    def test_pack_all_methods_callable(self):
        pack = CallCenterVerticalPack()
        assert callable(pack.get_pipeline_templates)
        assert callable(pack.get_alert_presets)
        assert callable(pack.get_dashboard_config)
        assert callable(pack.get_report_templates)
        assert callable(pack.get_quality_rubric)
