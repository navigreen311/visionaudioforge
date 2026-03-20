"""Call scoring and coaching report generation for the call-centre vertical."""

from __future__ import annotations

from typing import Any


class CallScoringService:
    """Score calls against a quality rubric and generate coaching insights."""

    # Keywords loosely associated with each default rubric category.
    _CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "greeting": ["hello", "hi", "welcome", "good morning", "good afternoon", "name"],
        "problem_identification": ["issue", "problem", "concern", "help", "understand", "question"],
        "resolution": ["solution", "resolve", "fixed", "completed", "done", "answer"],
        "compliance": ["disclosure", "terms", "policy", "regulation", "required", "notice"],
        "closing": ["thank", "goodbye", "anything else", "pleasure", "have a great"],
        "tone": ["please", "appreciate", "happy", "glad", "sorry", "understand"],
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def score_call(
        transcript_segments: list[dict[str, Any]],
        rubric: dict[str, Any],
    ) -> dict[str, Any]:
        """Score a single call against the provided rubric.

        Parameters
        ----------
        transcript_segments:
            List of dicts, each with at least ``"text"`` (str) and optionally
            ``"sentiment"`` (float, -1..1).
        rubric:
            Quality rubric as returned by
            ``CallCenterVerticalPack.get_quality_rubric()``.

        Returns
        -------
        dict with ``overall_score`` (0-100), ``category_scores``, ``highlights``,
        and ``improvements``.
        """
        full_text = " ".join(
            seg.get("text", "") for seg in transcript_segments
        ).lower()

        avg_sentiment = _avg_sentiment(transcript_segments)

        category_scores: dict[str, float] = {}
        highlights: list[str] = []
        improvements: list[str] = []

        for cat in rubric.get("categories", []):
            cat_name: str = cat["name"]
            keywords = CallScoringService._CATEGORY_KEYWORDS.get(cat_name, [])

            # Keyword-presence score (0-1)
            if keywords:
                hits = sum(1 for kw in keywords if kw in full_text)
                keyword_score = min(hits / max(len(keywords) * 0.5, 1), 1.0)
            else:
                keyword_score = 0.5  # neutral when no keywords defined

            # Blend with sentiment (sentiment mapped 0-1)
            sentiment_factor = (avg_sentiment + 1) / 2  # map -1..1 → 0..1
            raw = keyword_score * 0.7 + sentiment_factor * 0.3
            score = round(raw * 100, 1)
            category_scores[cat_name] = score

            if score >= 70:
                highlights.append(f"Strong {cat_name}: {cat['criteria']}")
            else:
                improvements.append(f"Improve {cat_name}: {cat['criteria']}")

        # Weighted overall score
        overall = 0.0
        for cat in rubric.get("categories", []):
            overall += cat["weight"] * category_scores.get(cat["name"], 0)

        return {
            "overall_score": round(overall, 1),
            "category_scores": category_scores,
            "highlights": highlights,
            "improvements": improvements,
        }

    @staticmethod
    def generate_coaching_report(
        call_scores: list[dict[str, Any]],
        agent_id: str,
    ) -> dict[str, Any]:
        """Aggregate multiple call scores into a coaching report.

        Parameters
        ----------
        call_scores:
            List of score dicts as returned by ``score_call``.
        agent_id:
            Identifier for the agent being evaluated.

        Returns
        -------
        dict with ``agent_id``, ``period_avg_score``, ``trend``,
        ``strengths``, ``areas_for_improvement``, ``recommended_training``.
        """
        if not call_scores:
            return {
                "agent_id": agent_id,
                "period_avg_score": 0.0,
                "trend": "insufficient_data",
                "strengths": [],
                "areas_for_improvement": [],
                "recommended_training": [],
            }

        overall_scores = [cs["overall_score"] for cs in call_scores]
        period_avg = round(sum(overall_scores) / len(overall_scores), 1)

        # Trend: compare first half to second half
        mid = max(len(overall_scores) // 2, 1)
        first_half_avg = sum(overall_scores[:mid]) / mid
        second_half_avg = sum(overall_scores[mid:]) / max(len(overall_scores[mid:]), 1)
        if second_half_avg > first_half_avg + 2:
            trend = "improving"
        elif second_half_avg < first_half_avg - 2:
            trend = "declining"
        else:
            trend = "stable"

        # Aggregate category scores across calls
        cat_totals: dict[str, list[float]] = {}
        for cs in call_scores:
            for cat_name, cat_score in cs.get("category_scores", {}).items():
                cat_totals.setdefault(cat_name, []).append(cat_score)

        cat_avgs = {
            name: round(sum(vals) / len(vals), 1)
            for name, vals in cat_totals.items()
        }

        strengths = [name for name, avg in cat_avgs.items() if avg >= 70]
        areas_for_improvement = [name for name, avg in cat_avgs.items() if avg < 70]

        _TRAINING_MAP: dict[str, str] = {
            "greeting": "Customer engagement basics",
            "problem_identification": "Active listening techniques",
            "resolution": "Product knowledge refresher",
            "compliance": "Regulatory compliance training",
            "closing": "Call closing best practices",
            "tone": "Empathy and communication skills",
        }
        recommended_training = [
            _TRAINING_MAP[area]
            for area in areas_for_improvement
            if area in _TRAINING_MAP
        ]

        return {
            "agent_id": agent_id,
            "period_avg_score": period_avg,
            "trend": trend,
            "strengths": strengths,
            "areas_for_improvement": areas_for_improvement,
            "recommended_training": recommended_training,
        }

    @staticmethod
    def compute_csat_estimate(sentiment_scores: list[float]) -> float:
        """Map a list of sentiment scores (-1..1) to a CSAT estimate (1-5).

        Mapping:
            very_positive (>0.6)  → 5
            positive (0.2..0.6)   → 4
            neutral (-0.2..0.2)   → 3
            negative (-0.6..-0.2) → 2
            very_negative (<-0.6) → 1
        """
        if not sentiment_scores:
            return 3.0

        def _to_csat(s: float) -> float:
            if s > 0.6:
                return 5.0
            if s > 0.2:
                return 4.0
            if s > -0.2:
                return 3.0
            if s > -0.6:
                return 2.0
            return 1.0

        mapped = [_to_csat(s) for s in sentiment_scores]
        return round(sum(mapped) / len(mapped), 1)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _avg_sentiment(segments: list[dict[str, Any]]) -> float:
    """Return average sentiment from transcript segments, default 0."""
    sentiments = [
        seg["sentiment"]
        for seg in segments
        if "sentiment" in seg and isinstance(seg["sentiment"], (int, float))
    ]
    if not sentiments:
        return 0.0
    return sum(sentiments) / len(sentiments)
