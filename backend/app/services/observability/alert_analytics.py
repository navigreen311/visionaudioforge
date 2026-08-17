"""Alert fatigue analytics.

Analyses alert patterns to detect fatigue indicators and suggests rule
tuning to reduce noise.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertRule, AlertStatus

logger = logging.getLogger(__name__)

#: Returned wherever a figure has no recorded source.
UNMEASURED: None = None

#: Alerts from one rule above this count in the window are treated as noisy.
NOISY_RULE_THRESHOLD = 20

#: Deterministic tuning policy: raise a noisy rule's threshold by this fraction.
THRESHOLD_BUMP_PCT = 20.0


async def _count(db: AsyncSession, stmt: Any) -> int | None:
    """Run a COUNT statement, returning None if the query cannot be executed."""
    try:
        return (await db.execute(stmt)).scalar() or 0
    except Exception:
        logger.warning("Alert analytics query failed", exc_info=True)
        return None


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
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        scope = (Alert.workspace_id == workspace_id, Alert.created_at >= cutoff)

        total_alerts = await _count(
            db, select(func.count()).select_from(Alert).where(*scope)
        )
        acknowledged = await _count(
            db,
            select(func.count())
            .select_from(Alert)
            .where(*scope, Alert.status != AlertStatus.new),
        )

        if total_alerts is None or acknowledged is None:
            acknowledged_pct = UNMEASURED
        elif total_alerts == 0:
            acknowledged_pct = UNMEASURED
        else:
            acknowledged_pct = round(acknowledged / total_alerts * 100, 2)

        # Acknowledgement timestamps are not recorded on the alerts table
        # (only `acknowledged_by`), so response time cannot be derived.
        avg_response_time_s = UNMEASURED

        noisy_rules = await AlertAnalytics._noisy_rules(db, scope)

        # Fatigue score (0-100). Each factor contributes only when its input was
        # actually measured, and `score_basis` records which ones counted so a
        # partial score is never mistaken for a complete one.
        unmeasured: list[str] = []
        score = 0.0
        score_basis: list[str] = []

        if total_alerts is None:
            unmeasured.append("total_alerts")
        else:
            score += min(total_alerts / 300, 1.0) * 30
            score_basis.append("volume")

        if acknowledged_pct is None:
            unmeasured.append("acknowledged_pct")
        else:
            score += (1 - acknowledged_pct / 100) * 30
            score_basis.append("acknowledgement_rate")

        if avg_response_time_s is None:
            unmeasured.append("avg_response_time_s")
        else:
            score += min(avg_response_time_s / 600, 1.0) * 20
            score_basis.append("response_time")

        score += min(len(noisy_rules) / 3, 1.0) * 20
        score_basis.append("noisy_rules")

        fatigue_score = round(min(score, 100), 1)

        recommendations: list[str] = []
        if fatigue_score > 70:
            recommendations.append(
                "Critical: alert fatigue is high — review noisy rules immediately"
            )
        if acknowledged_pct is not None and acknowledged_pct < 50:
            recommendations.append(
                "Low acknowledgement rate — consider reducing alert volume"
            )
        if avg_response_time_s is not None and avg_response_time_s > 300:
            recommendations.append(
                "Slow response times — escalate or auto-resolve low-severity alerts"
            )
        for nr in noisy_rules:
            if nr["count"] > NOISY_RULE_THRESHOLD:
                recommendations.append(
                    f"Rule '{nr['rule']}' is noisy ({nr['count']} alerts) — raise threshold or add cooldown"
                )
        if unmeasured:
            recommendations.append(
                "Partial data: "
                + ", ".join(unmeasured)
                + " could not be measured, so this score is incomplete"
            )
        elif not recommendations:
            recommendations.append("Alert hygiene is healthy — no action needed")

        return {
            "total_alerts": total_alerts,
            "acknowledged_pct": acknowledged_pct,
            "avg_response_time_s": avg_response_time_s,
            "noisy_rules": noisy_rules,
            "fatigue_score": fatigue_score,
            "score_basis": score_basis,
            "unmeasured": unmeasured,
            "period_days": days,
            "recommendations": recommendations,
        }

    @staticmethod
    async def _noisy_rules(
        db: AsyncSession, scope: tuple[Any, ...]
    ) -> list[dict[str, Any]]:
        """Rules that fired most often in the window, measured from the DB."""
        try:
            rows = (
                await db.execute(
                    select(
                        AlertRule.name,
                        func.count(Alert.id).label("count"),
                        func.count(Alert.acknowledged_by).label("acknowledged"),
                    )
                    .join(AlertRule, AlertRule.id == Alert.rule_id)
                    .where(*scope)
                    .group_by(AlertRule.name)
                    .order_by(func.count(Alert.id).desc())
                    .limit(5)
                )
            ).all()
        except Exception:
            logger.warning("Noisy-rule query failed", exc_info=True)
            return []

        return [
            {
                "rule": name,
                "count": count,
                "ack_rate": round(acknowledged / count, 2) if count else UNMEASURED,
            }
            for name, count, acknowledged in rows
        ]

    # ------------------------------------------------------------------
    # Rule tuning suggestion
    # ------------------------------------------------------------------

    @staticmethod
    async def suggest_rule_tuning(
        db: AsyncSession,
        rule_id: UUID,
    ) -> dict[str, Any]:
        """Suggest a threshold adjustment for a noisy alert rule.

        The current threshold is read from the rule's own ``conditions``. If it
        cannot be read there is nothing to tune against, and the suggestion is
        reported as unavailable rather than being made up — a fabricated
        "current threshold" would misrepresent the user's own configuration.
        """
        current_threshold = await AlertAnalytics._rule_threshold(db, rule_id)

        if current_threshold is None:
            return {
                "status": "unavailable",
                "current_threshold": UNMEASURED,
                "suggested_threshold": UNMEASURED,
                "expected_reduction_pct": UNMEASURED,
                "reason": (
                    "No numeric threshold found in this rule's conditions, so no "
                    "tuning suggestion can be derived."
                ),
            }

        # Deterministic policy, not an estimate derived from data we lack.
        suggested = round(current_threshold * (1 + THRESHOLD_BUMP_PCT / 100), 1)

        return {
            "status": "suggested",
            "current_threshold": current_threshold,
            "suggested_threshold": suggested,
            "expected_reduction_pct": UNMEASURED,
            "reason": (
                f"Standard tuning policy: raise the threshold by "
                f"{THRESHOLD_BUMP_PCT:g}% to reduce firing frequency. The actual "
                "noise reduction is not predicted — that needs historical "
                "distribution analysis which is not implemented."
            ),
        }

    @staticmethod
    async def _rule_threshold(db: AsyncSession, rule_id: UUID) -> float | None:
        """Read a numeric ``threshold`` out of an alert rule's conditions."""
        try:
            rule = (
                await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
            ).scalar_one_or_none()
        except Exception:
            logger.warning("Could not load alert rule %s", rule_id, exc_info=True)
            return None

        conditions = getattr(rule, "conditions", None)
        if not isinstance(conditions, dict):
            return None
        value = conditions.get("threshold")
        return float(value) if isinstance(value, (int, float)) else None
