"""Billing service: plan limits, usage tracking, upgrade management."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import PlanType, Workspace


PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "price": 0,
        "limits": {
            "assets": 100,
            "models": 3,
            "pipelines": 5,
            "api_calls_daily": 1000,
            "storage_gb": 1,
        },
    },
    "pro": {
        "price": 49,
        "limits": {
            "assets": 10000,
            "models": 50,
            "pipelines": 100,
            "api_calls_daily": 50000,
            "storage_gb": 50,
        },
    },
    "enterprise": {
        "price": 299,
        "limits": {
            "assets": -1,
            "models": -1,
            "pipelines": -1,
            "api_calls_daily": -1,
            "storage_gb": 500,
        },
    },
}


class BillingService:
    """Plan-based billing, usage tracking, and limit enforcement."""

    @staticmethod
    async def check_limit(
        db: AsyncSession,
        workspace_id: str | UUID,
        resource: str,
    ) -> dict[str, Any]:
        """Check if a workspace is within its plan limit for a resource."""
        result = await db.execute(
            select(Workspace).where(Workspace.id == UUID(str(workspace_id)))
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            return {"allowed": False, "current": 0, "limit": 0, "plan": "unknown"}

        plan_name = workspace.plan.value if hasattr(workspace.plan, "value") else str(workspace.plan)
        plan = PLANS.get(plan_name, PLANS["free"])
        limit = plan["limits"].get(resource, 0)

        # Get current usage from workspace settings
        usage = (workspace.settings or {}).get("usage", {})
        current = usage.get(resource, 0)

        # -1 means unlimited
        allowed = limit == -1 or current < limit

        return {
            "allowed": allowed,
            "current": current,
            "limit": limit,
            "plan": plan_name,
        }

    @staticmethod
    async def get_usage(
        db: AsyncSession,
        workspace_id: str | UUID,
    ) -> dict[str, Any]:
        """Return current usage, limits, and percentages for a workspace."""
        result = await db.execute(
            select(Workspace).where(Workspace.id == UUID(str(workspace_id)))
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            return {"plan": "unknown", "usage": {}, "limits": {}, "usage_pct": {}}

        plan_name = workspace.plan.value if hasattr(workspace.plan, "value") else str(workspace.plan)
        plan = PLANS.get(plan_name, PLANS["free"])
        limits = plan["limits"]
        usage = (workspace.settings or {}).get("usage", {})

        usage_pct = {}
        for resource, limit in limits.items():
            current = usage.get(resource, 0)
            if limit == -1:
                usage_pct[resource] = 0.0
            elif limit == 0:
                usage_pct[resource] = 100.0
            else:
                usage_pct[resource] = round((current / limit) * 100, 1)

        return {
            "plan": plan_name,
            "usage": usage,
            "limits": limits,
            "usage_pct": usage_pct,
        }

    @staticmethod
    async def track_api_call(
        db: AsyncSession,
        workspace_id: str | UUID,
    ) -> None:
        """Increment the daily API call counter for a workspace.

        V1: uses workspace settings JSON. Production should use Redis INCR with TTL.
        """
        result = await db.execute(
            select(Workspace).where(Workspace.id == UUID(str(workspace_id)))
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            return

        settings = dict(workspace.settings or {})
        usage = dict(settings.get("usage", {}))
        usage["api_calls_daily"] = usage.get("api_calls_daily", 0) + 1
        settings["usage"] = usage

        await db.execute(
            update(Workspace)
            .where(Workspace.id == workspace.id)
            .values(settings=settings)
        )
        await db.commit()

    @staticmethod
    async def get_billing_dashboard(
        db: AsyncSession,
        workspace_id: str | UUID,
    ) -> dict[str, Any]:
        """Return a billing dashboard with plan, usage, overage, and recommendations."""
        usage_info = await BillingService.get_usage(db, workspace_id)
        plan_name = usage_info["plan"]
        plan = PLANS.get(plan_name, PLANS["free"])

        overage: dict[str, Any] = {}
        recommendations: list[str] = []

        for resource, limit in usage_info["limits"].items():
            current = usage_info["usage"].get(resource, 0)
            if limit != -1 and current > limit:
                overage[resource] = current - limit

        pct = usage_info.get("usage_pct", {})
        for resource, pct_val in pct.items():
            if pct_val > 80 and plan_name != "enterprise":
                recommendations.append(
                    f"{resource} usage at {pct_val}% — consider upgrading to "
                    f"{'pro' if plan_name == 'free' else 'enterprise'}"
                )

        return {
            "plan": plan_name,
            "price": plan["price"],
            "usage": usage_info["usage"],
            "overage": overage,
            "recommendations": recommendations,
        }

    @staticmethod
    async def upgrade_plan(
        db: AsyncSession,
        workspace_id: str | UUID,
        new_plan: str,
    ) -> dict[str, Any]:
        """Upgrade a workspace to a new plan."""
        if new_plan not in PLANS:
            raise ValueError(f"Invalid plan: {new_plan}. Valid: {list(PLANS.keys())}")

        result = await db.execute(
            select(Workspace).where(Workspace.id == UUID(str(workspace_id)))
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            raise ValueError("Workspace not found")

        previous = workspace.plan.value if hasattr(workspace.plan, "value") else str(workspace.plan)

        await db.execute(
            update(Workspace)
            .where(Workspace.id == workspace.id)
            .values(plan=PlanType(new_plan))
        )
        await db.commit()

        return {
            "previous": previous,
            "new": new_plan,
            "effective_at": datetime.utcnow().isoformat(),
            "note": "Plan updated. Billing changes take effect immediately.",
        }
