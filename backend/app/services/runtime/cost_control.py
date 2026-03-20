"""Cost Controller — track inference spend, enforce budgets and quotas."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


class CostController:
    """Track and control inference costs per workspace."""

    def __init__(self, cost_per_unit: dict[str, float] | None = None) -> None:
        # model_id -> cost per inference (override per-model)
        self._cost_table: dict[str, float] = cost_per_unit or {}

        # In-memory ledger: workspace_id -> list of events
        self._ledger: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Quotas: workspace_id -> {"limit": int, "used": int, "resets_at": str}
        self._quotas: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Cost table helpers
    # ------------------------------------------------------------------

    def set_model_cost(self, model_id: str, cost: float) -> None:
        """Set or update cost per inference for a model."""
        self._cost_table[model_id] = cost

    def _unit_cost(self, model_id: str) -> float:
        return self._cost_table.get(model_id, 0.001)  # default fallback

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    def track_inference(
        self,
        workspace_id: str,
        model_id: str,
        latency_ms: float,
        tokens_or_pixels: int,
    ) -> None:
        """Log an inference cost event."""
        cost = self._unit_cost(model_id)
        event = {
            "model_id": model_id,
            "latency_ms": latency_ms,
            "tokens_or_pixels": tokens_or_pixels,
            "cost": cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._ledger[workspace_id].append(event)
        logger.debug("Tracked inference for %s on %s: $%.4f", workspace_id, model_id, cost)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_workspace_cost(
        self,
        db: Any,
        workspace_id: str,
        period: str = "daily",
    ) -> dict[str, Any]:
        """Aggregate costs for a workspace over a period."""
        events = self._ledger.get(workspace_id, [])
        now = datetime.now(timezone.utc)

        if period == "daily":
            cutoff = now - timedelta(days=1)
        elif period == "weekly":
            cutoff = now - timedelta(weeks=1)
        elif period == "monthly":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = now - timedelta(days=1)

        filtered = [
            e for e in events
            if datetime.fromisoformat(e["timestamp"]) >= cutoff
        ]

        total_cost = sum(e["cost"] for e in filtered)
        by_model: dict[str, float] = defaultdict(float)
        for e in filtered:
            by_model[e["model_id"]] += e["cost"]

        count = len(filtered)
        avg = total_cost / count if count else 0.0

        return {
            "total_cost": round(total_cost, 6),
            "by_model": dict(by_model),
            "inference_count": count,
            "avg_cost_per_inference": round(avg, 6),
        }

    def check_budget(
        self,
        db: Any,
        workspace_id: str,
        budget_limit: float,
    ) -> dict[str, Any]:
        """Check whether workspace is within budget."""
        report = self.get_workspace_cost(db, workspace_id, period="daily")
        spent = report["total_cost"]
        remaining = max(budget_limit - spent, 0.0)
        count = report["inference_count"]

        # Project daily spend based on current rate
        hours_elapsed = max(datetime.now(timezone.utc).hour, 1)
        projected = (spent / hours_elapsed) * 24 if hours_elapsed else spent

        return {
            "within_budget": spent <= budget_limit,
            "spent": round(spent, 6),
            "remaining": round(remaining, 6),
            "projected_daily": round(projected, 6),
        }

    # ------------------------------------------------------------------
    # Quotas (in-memory; production would use Redis)
    # ------------------------------------------------------------------

    def set_quota(self, workspace_id: str, daily_limit: int) -> None:
        """Set daily inference quota for a workspace."""
        resets_at = (
            datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        )
        self._quotas[workspace_id] = {
            "limit": daily_limit,
            "used": 0,
            "resets_at": resets_at.isoformat(),
        }

    def check_quota(self, workspace_id: str) -> dict[str, Any]:
        """Check quota status for a workspace."""
        quota = self._quotas.get(workspace_id)
        if quota is None:
            return {
                "allowed": True,
                "used": 0,
                "limit": 0,
                "resets_at": "",
            }

        # Auto-reset if past reset time
        resets_at = datetime.fromisoformat(quota["resets_at"])
        if datetime.now(timezone.utc) >= resets_at:
            quota["used"] = 0
            quota["resets_at"] = (resets_at + timedelta(days=1)).isoformat()

        allowed = quota["used"] < quota["limit"]
        if allowed:
            quota["used"] += 1

        return {
            "allowed": allowed,
            "used": quota["used"],
            "limit": quota["limit"],
            "resets_at": quota["resets_at"],
        }

    # ------------------------------------------------------------------
    # Full cost report
    # ------------------------------------------------------------------

    def generate_cost_report(
        self,
        db: Any,
        workspace_id: str,
        period: str = "monthly",
    ) -> dict[str, Any]:
        """Generate a comprehensive cost report."""
        events = self._ledger.get(workspace_id, [])
        now = datetime.now(timezone.utc)

        if period == "daily":
            cutoff = now - timedelta(days=1)
        elif period == "weekly":
            cutoff = now - timedelta(weeks=1)
        else:
            cutoff = now - timedelta(days=30)

        filtered = [
            e for e in events
            if datetime.fromisoformat(e["timestamp"]) >= cutoff
        ]

        total_cost = sum(e["cost"] for e in filtered)
        by_model: dict[str, float] = defaultdict(float)
        by_day: dict[str, float] = defaultdict(float)

        for e in filtered:
            by_model[e["model_id"]] += e["cost"]
            day_key = datetime.fromisoformat(e["timestamp"]).strftime("%Y-%m-%d")
            by_day[day_key] += e["cost"]

        # Compute trend
        day_values = sorted(by_day.items())
        if len(day_values) >= 2:
            first_half = sum(v for _, v in day_values[: len(day_values) // 2])
            second_half = sum(v for _, v in day_values[len(day_values) // 2 :])
            trend = "increasing" if second_half > first_half else "decreasing"
        else:
            trend = "stable"

        # Recommendations
        recommendations: list[str] = []
        if total_cost > 100:
            recommendations.append("Consider using lower-cost model variants for non-critical workloads")
        if len(by_model) > 3:
            recommendations.append("Consolidate model usage to reduce overhead")
        if not recommendations:
            recommendations.append("Costs are within normal range")

        return {
            "period": period,
            "total_cost": round(total_cost, 6),
            "by_model": dict(by_model),
            "by_day": [{"date": d, "cost": round(c, 6)} for d, c in sorted(by_day.items())],
            "trend": trend,
            "recommendations": recommendations,
        }
