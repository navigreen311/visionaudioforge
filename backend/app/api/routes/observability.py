"""Observability routes — SRE dashboard, SLA, alert fatigue analytics."""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.services.observability.dashboard import SREDashboardService
from app.services.observability.sla import SLAService, STANDARD_SLAS
from app.services.observability.alert_analytics import AlertAnalytics

router = APIRouter(prefix="/api/observability", tags=["observability"])

# ------------------------------------------------------------------
# Dashboard endpoints
# ------------------------------------------------------------------


@router.get("/dashboard")
async def system_overview(
    db: AsyncSession = Depends(get_async_session),
):
    """System-level health and performance overview."""
    return await SREDashboardService.get_system_overview(db)


@router.get("/pipeline-health")
async def pipeline_health(
    db: AsyncSession = Depends(get_async_session),
):
    """Pipeline execution metrics."""
    return await SREDashboardService.get_pipeline_health(db)


@router.get("/inference")
async def inference_metrics():
    """ML inference metrics."""
    return await SREDashboardService.get_inference_metrics()


@router.get("/errors")
async def error_taxonomy(
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_async_session),
):
    """Categorised error breakdown."""
    return await SREDashboardService.get_error_taxonomy(db, hours=hours)


@router.get("/queues")
async def queue_metrics():
    """Celery / task-queue metrics."""
    return await SREDashboardService.get_queue_metrics()


# ------------------------------------------------------------------
# SLA endpoints
# ------------------------------------------------------------------


@router.get("/sla")
async def sla_compliance(
    tier: str = Query("standard", description="SLA tier: basic, standard, premium"),
    period_hours: int = Query(24, ge=1),
    db: AsyncSession = Depends(get_async_session),
):
    """Check SLA compliance for the given tier."""
    sla_def = STANDARD_SLAS.get(tier)
    if sla_def is None:
        return {"error": f"Unknown SLA tier '{tier}'. Choose basic, standard, or premium."}
    config = SLAService.define_sla(
        name=tier,
        target_uptime=sla_def["uptime"],
        max_latency_ms=sla_def["latency"],
        max_error_rate=sla_def["error_rate"],
    )
    return await SLAService.check_sla_compliance(db, config, period_hours=period_hours)


@router.post("/sla/report")
async def sla_report(
    period: str = Query("weekly", description="daily, weekly, or monthly"),
    db: AsyncSession = Depends(get_async_session),
):
    """Generate an SLA report for the requested period."""
    return await SLAService.generate_sla_report(db, period=period)


# ------------------------------------------------------------------
# Alert fatigue
# ------------------------------------------------------------------


@router.get("/alert-fatigue")
async def alert_fatigue(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_async_session),
):
    """Analyse alert fatigue for a workspace."""
    return await AlertAnalytics.analyze_alert_fatigue(db, workspace_id, days=days)


# ------------------------------------------------------------------
# Request volume (OB3)
# ------------------------------------------------------------------


def _mock_request_volume() -> list[dict[str, int]]:
    """Generate 24 hours of mock request-volume data."""
    now_hour = datetime.now(timezone.utc).hour
    buckets: list[dict[str, int]] = []
    for h in range(24):
        base = random.randint(200, 1200) if h != now_hour else random.randint(80, 400)
        errors = max(0, int(base * random.uniform(0.01, 0.08)))
        buckets.append({"hour": h, "success": base - errors, "errors": errors})
    return buckets


@router.get("/request-volume")
async def request_volume() -> dict[str, object]:
    """Hourly request volume for the last 24 hours (mock data)."""
    return {
        "period": "24h",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "buckets": _mock_request_volume(),
    }


# ------------------------------------------------------------------
# SLA history (OB4)
# ------------------------------------------------------------------


def _mock_sla_history(days: int = 7) -> list[dict[str, object]]:
    """Generate daily SLA compliance percentages."""
    today = datetime.now(timezone.utc).date()
    history: list[dict[str, object]] = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        # Mostly above 99.9, occasionally dip below
        pct = round(random.uniform(99.5, 100.0), 3) if random.random() < 0.7 else round(random.uniform(98.5, 99.85), 3)
        pct = min(pct, 100.0)
        history.append({"date": day.isoformat(), "pct": pct})
    return history


@router.get("/sla-history")
async def sla_history(
    days: int = Query(7, ge=1, le=90, description="Number of days of history"),
) -> dict[str, object]:
    """Daily SLA compliance history (mock data)."""
    return {
        "days": days,
        "target_pct": 99.9,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "history": _mock_sla_history(days),
    }
