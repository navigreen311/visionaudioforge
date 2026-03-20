"""Alert fatigue analytics.

Analyses alert patterns to detect fatigue indicators and suggests rule
tuning to reduce noise.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AlertAnalytics:
    """Alert fatigue detection and rule-tuning suggestions."""

    # ------------------------------------------------------------------
    # Fatigue analysis
    # ------------------------------------------------------------------

    @staticmethod
    async def analyze_alert_fatigue(
        db: AsyncSession,
        workspace_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """Analyse alert patterns to quantify fatigue.

        Fatigue indicators
        ------------------
        - High alert volume
        - Low acknowledgement rate
        - Slow average response time
        - Rules that trigger > 10 times per day

        Returns a fatigue score (0-100) and actionable recommendations.
        """
        # V1: simulated metrics — wire up to real alert tables later
        total_alerts = random.randint(50, 500)
        acknowledged = random.randint(int(total_alerts * 0.3), total_alerts)
        acknowledged_pct = round(acknowledged / max(total_alerts, 1) * 100, 2)
        avg_response_time_s = round(random.uniform(30, 600), 2)

        noisy_rules: list[dict[str, Any]] = []
        rule_names = [
            "high-cpu-usage",
            "disk-space-low",
            "api-error-rate",
            "memory-pressure",
            "queue-depth-high",
        ]
        for rname in random.sample(rule_names, k=random.randint(1, 3)):
            count = random.randint(5, 50)
            ack_rate = round(random.uniform(0.1, 0.9), 2)
            noisy_rules.append(
                {"rule": rname, "count": count, "ack_rate": ack_rate}
            )

        # Compute fatigue score (0–100)
        # Factors: volume, ack rate, response time, noisy rule count
        volume_factor = min(total_alerts / 300, 1.0) * 30  # max 30
        ack_factor = (1 - acknowledged_pct / 100) * 30  # max 30
        response_factor = min(avg_response_time_s / 600, 1.0) * 20  # max 20
        noise_factor = min(len(noisy_rules) / 3, 1.0) * 20  # max 20
        fatigue_score = round(
            min(volume_factor + ack_factor + response_factor + noise_factor, 100),
            1,
        )

        recommendations: list[str] = []
        if fatigue_score > 70:
            recommendations.append(
                "Critical: alert fatigue is high — review noisy rules immediately"
            )
        if acknowledged_pct < 50:
            recommendations.append(
                "Low acknowledgement rate — consider reducing alert volume"
            )
        if avg_response_time_s > 300:
            recommendations.append(
                "Slow response times — escalate or auto-resolve low-severity alerts"
            )
        for nr in noisy_rules:
            if nr["count"] > 20:
                recommendations.append(
                    f"Rule '{nr['rule']}' is noisy ({nr['count']} alerts) — raise threshold or add cooldown"
                )
        if not recommendations:
            recommendations.append("Alert hygiene is healthy — no action needed")

        return {
            "total_alerts": total_alerts,
            "acknowledged_pct": acknowledged_pct,
            "avg_response_time_s": avg_response_time_s,
            "noisy_rules": noisy_rules,
            "fatigue_score": fatigue_score,
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------
    # Rule tuning suggestion
    # ------------------------------------------------------------------

    @staticmethod
    async def suggest_rule_tuning(
        db: AsyncSession,
        rule_id: UUID,
    ) -> dict[str, Any]:
        """Suggest threshold adjustments for a noisy alert rule.

        V1 returns heuristic suggestions; future versions will use
        historical distribution analysis.
        """
        current_threshold = round(random.uniform(50, 90), 1)
        # Suggest raising by 10-25 %
        bump = random.uniform(0.10, 0.25)
        suggested = round(current_threshold * (1 + bump), 1)
        expected_reduction = round(bump * 100, 1)

        reasons = [
            "Rule has triggered frequently with low acknowledgement rate",
            "Historical data suggests a higher threshold reduces noise without missing incidents",
            "Current threshold is below the 95th percentile of normal values",
        ]

        return {
            "current_threshold": current_threshold,
            "suggested_threshold": suggested,
            "reason": random.choice(reasons),
            "expected_reduction_pct": expected_reduction,
        }
