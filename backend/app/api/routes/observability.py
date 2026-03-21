"""Observability routes — SRE dashboard, SLA, alert fatigue analytics."""

import math
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
# Latency history (mock)
# ------------------------------------------------------------------

RANGE_HOURS = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}


@router.get("/latency-history")
async def latency_history(
    range: str = Query("24h", description="Preset range: 1h, 6h, 24h, 7d"),
    from_dt: Optional[str] = Query(None, alias="from", description="ISO start (custom range)"),
    to_dt: Optional[str] = Query(None, alias="to", description="ISO end (custom range)"),
) -> dict:
    """Return mock latency time-series with 24 data points."""
    hours = RANGE_HOURS.get(range, 24)

    if from_dt and to_dt:
        try:
            start = datetime.fromisoformat(from_dt)
            end = datetime.fromisoformat(to_dt)
            hours = max(1, int((end - start).total_seconds() / 3600))
        except ValueError:
            pass

    now = datetime.now(timezone.utc)
    points = 24
    step = timedelta(hours=hours) / points

    rng = random.Random(42)  # deterministic seed for stable demo data
    data = []
    for i in range(points):
        ts = now - timedelta(hours=hours) + step * i
        base_avg = 120 + 30 * math.sin(i * 0.5) + rng.gauss(0, 10)
        base_p99 = base_avg * (1.8 + rng.gauss(0, 0.15))
        data.append(
            {
                "timestamp": ts.isoformat(),
                "avg_ms": round(max(10, base_avg), 1),
                "p99_ms": round(max(20, base_p99), 1),
            }
        )

    return {"range": range, "points": points, "data": data}
