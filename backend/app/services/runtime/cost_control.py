"""Cost Controller — track inference spend, enforce budgets and quotas.

Everything here was per-instance state. That made the quota not a quota: every
restart returned every workspace to unlimited, and each worker counted its own
usage, so a four-worker deployment allowed roughly four times the configured
limit. The spend ledger failed the same way in reverse — cost reports read as
"nothing spent" after a deploy.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime import InferenceCostEvent, ModelCostRate, WorkspaceQuota

logger = logging.getLogger(__name__)

#: Charged when a model has no explicit rate.
DEFAULT_UNIT_COST = 0.001


def _cutoff_for(period: str, now: datetime) -> datetime:
    if period == "daily":
        return now - timedelta(days=1)
    if period == "weekly":
        return now - timedelta(weeks=1)
    if period == "monthly":
        return now - timedelta(days=30)
    return now - timedelta(days=1)


class CostController:
    """Track and control inference costs per workspace."""

    # ------------------------------------------------------------------
    # Cost table helpers
    # ------------------------------------------------------------------

    async def set_model_cost(
        self, db: AsyncSession, model_id: str, cost: float
    ) -> None:
        """Set or update cost per inference for a model."""
        row = (
            await db.execute(
                select(ModelCostRate).where(ModelCostRate.model_id == model_id)
            )
        ).scalar_one_or_none()

        if row is None:
            row = ModelCostRate(model_id=model_id)
            db.add(row)
        row.cost_per_unit = cost
        await db.commit()

    async def _unit_cost(self, db: AsyncSession, model_id: str) -> float:
        row = (
            await db.execute(
                select(ModelCostRate).where(ModelCostRate.model_id == model_id)
            )
        ).scalar_one_or_none()
        return row.cost_per_unit if row is not None else DEFAULT_UNIT_COST

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    async def track_inference(
        self,
        db: AsyncSession,
        workspace_id: str,
        model_id: str,
        latency_ms: float,
        tokens_or_pixels: int,
    ) -> None:
        """Log an inference cost event."""
        cost = await self._unit_cost(db, model_id)
        db.add(
            InferenceCostEvent(
                workspace_id=workspace_id,
                model_id=model_id,
                latency_ms=latency_ms,
                tokens_or_pixels=tokens_or_pixels,
                cost=cost,
            )
        )
        await db.commit()
        logger.debug(
            "Tracked inference for %s on %s: $%.4f", workspace_id, model_id, cost
        )

    async def _events_since(
        self, db: AsyncSession, workspace_id: str, cutoff: datetime
    ) -> list[InferenceCostEvent]:
        return list(
            (
                await db.execute(
                    select(InferenceCostEvent).where(
                        InferenceCostEvent.workspace_id == workspace_id,
                        InferenceCostEvent.timestamp >= cutoff,
                    )
                )
            )
            .scalars()
            .all()
        )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def get_workspace_cost(
        self,
        db: AsyncSession,
        workspace_id: str,
        period: str = "daily",
    ) -> dict[str, Any]:
        """Aggregate costs for a workspace over a period."""
        now = datetime.now(timezone.utc)
        events = await self._events_since(db, workspace_id, _cutoff_for(period, now))

        total_cost = sum(e.cost for e in events)
        by_model: dict[str, float] = defaultdict(float)
        for e in events:
            by_model[e.model_id] += e.cost

        count = len(events)
        avg = total_cost / count if count else 0.0

        return {
            "total_cost": round(total_cost, 6),
            "by_model": dict(by_model),
            "inference_count": count,
            "avg_cost_per_inference": round(avg, 6),
        }

    async def check_budget(
        self,
        db: AsyncSession,
        workspace_id: str,
        budget_limit: float,
    ) -> dict[str, Any]:
        """Check whether workspace is within budget."""
        report = await self.get_workspace_cost(db, workspace_id, period="daily")
        spent = report["total_cost"]
        remaining = max(budget_limit - spent, 0.0)

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
    # Quotas
    # ------------------------------------------------------------------

    async def set_quota(
        self, db: AsyncSession, workspace_id: str, daily_limit: int
    ) -> None:
        """Set daily inference quota for a workspace."""
        resets_at = (
            datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            + timedelta(days=1)
        )

        row = (
            await db.execute(
                select(WorkspaceQuota).where(
                    WorkspaceQuota.workspace_id == workspace_id
                )
            )
        ).scalar_one_or_none()

        if row is None:
            row = WorkspaceQuota(workspace_id=workspace_id)
            db.add(row)

        row.daily_limit = daily_limit
        row.used = 0
        row.resets_at = resets_at
        await db.commit()

    async def check_quota(
        self, db: AsyncSession, workspace_id: str
    ) -> dict[str, Any]:
        """Check quota status for a workspace, consuming one unit if allowed."""
        row = (
            await db.execute(
                select(WorkspaceQuota)
                .where(WorkspaceQuota.workspace_id == workspace_id)
                # Serialise concurrent checks so two workers cannot both read
                # the last remaining unit and both allow the call.
                .with_for_update()
            )
        ).scalar_one_or_none()

        if row is None:
            # No quota configured means no limit to enforce.
            return {"allowed": True, "used": 0, "limit": 0, "resets_at": ""}

        now = datetime.now(timezone.utc)
        if row.resets_at is not None and now >= row.resets_at:
            row.used = 0
            row.resets_at = row.resets_at + timedelta(days=1)

        allowed = row.used < row.daily_limit
        if allowed:
            row.used += 1

        await db.commit()

        return {
            "allowed": allowed,
            "used": row.used,
            "limit": row.daily_limit,
            "resets_at": row.resets_at.isoformat() if row.resets_at else "",
        }

    # ------------------------------------------------------------------
    # Full cost report
    # ------------------------------------------------------------------

    async def generate_cost_report(
        self,
        db: AsyncSession,
        workspace_id: str,
        period: str = "monthly",
    ) -> dict[str, Any]:
        """Generate a comprehensive cost report."""
        now = datetime.now(timezone.utc)
        events = await self._events_since(db, workspace_id, _cutoff_for(period, now))

        total_cost = sum(e.cost for e in events)
        by_model: dict[str, float] = defaultdict(float)
        by_day: dict[str, float] = defaultdict(float)

        for e in events:
            by_model[e.model_id] += e.cost
            by_day[e.timestamp.strftime("%Y-%m-%d")] += e.cost

        # Compute trend
        day_values = sorted(by_day.items())
        if len(day_values) >= 2:
            first_half = sum(v for _, v in day_values[: len(day_values) // 2])
            second_half = sum(v for _, v in day_values[len(day_values) // 2 :])
            trend = "increasing" if second_half > first_half else "decreasing"
        else:
            trend = "stable"

        recommendations: list[str] = []
        if total_cost > 100:
            recommendations.append(
                "Consider using lower-cost model variants for non-critical workloads"
            )
        if len(by_model) > 3:
            recommendations.append("Consolidate model usage to reduce overhead")
        if not recommendations:
            recommendations.append("Costs are within normal range")

        return {
            "period": period,
            "total_cost": round(total_cost, 6),
            "by_model": dict(by_model),
            "by_day": [
                {"date": d, "cost": round(c, 6)} for d, c in sorted(by_day.items())
            ],
            "trend": trend,
            "recommendations": recommendations,
        }
