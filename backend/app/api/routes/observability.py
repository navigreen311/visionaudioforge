"""Observability routes — SRE dashboard, SLA, alert fatigue analytics."""

from __future__ import annotations

import datetime as _dt
import math
import random
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.services.observability.dashboard import SREDashboardService
from app.services.observability.sla import SLAService, STANDARD_SLAS
from app.services.observability.alert_analytics import AlertAnalytics

router = APIRouter(prefix="/api/observability", tags=["observability"])

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_RANGE_MAP = {"1h": 1, "6h": 6, "12h": 12, "24h": 24, "48h": 48, "7d": 168}


def _parse_range_hours(range_str: str) -> int:
    """Convert a range string like '24h' or '7d' into hours."""
    return _RANGE_MAP.get(range_str, 24)


def _seed_rng(seed: int = 42) -> random.Random:
    """Deterministic RNG so mock data is stable across calls."""
    return random.Random(seed)


# ------------------------------------------------------------------
# Mock data generators (Observability Page stubs)
# ------------------------------------------------------------------


def _mock_metrics(hours: int) -> dict[str, Any]:
    rng = _seed_rng(hours)
    total_requests = rng.randint(80_000, 150_000)
    error_count = rng.randint(120, 400)
    return {
        "range_hours": hours,
        "total_requests": total_requests,
        "avg_latency_ms": round(rng.uniform(45, 130), 1),
        "p99_latency_ms": round(rng.uniform(180, 350), 1),
        "error_rate": round(error_count / total_requests * 100, 3),
        "uptime_pct": round(rng.uniform(99.85, 99.99), 3),
        "active_pipelines": rng.randint(4, 8),
        "healthy_services": 12,
        "degraded_services": rng.choice([0, 0, 1]),
        "down_services": 0,
        "cpu_usage_pct": round(rng.uniform(30, 65), 1),
        "memory_usage_pct": round(rng.uniform(50, 78), 1),
        "gpu_usage_pct": round(rng.uniform(20, 55), 1),
        "disk_usage_pct": round(rng.uniform(40, 60), 1),
    }


def _mock_latency_history(hours: int) -> dict[str, Any]:
    rng = _seed_rng(hours + 1)
    now = _dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    points = []
    for i in range(hours):
        ts = now - _dt.timedelta(hours=hours - 1 - i)
        # Simulate a latency spike around hour 7
        base_avg = 72.0 if i != 7 else 165.0
        base_p99 = 185.0 if i != 7 else 420.0
        points.append({
            "timestamp": ts.isoformat() + "Z",
            "avg_ms": round(base_avg + rng.uniform(-15, 25), 1),
            "p99_ms": round(base_p99 + rng.uniform(-20, 40), 1),
        })
    return {"points": points, "sla_target_ms": 200}


def _mock_request_volume(hours: int) -> dict[str, Any]:
    rng = _seed_rng(hours + 2)
    now = _dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    entries = []
    for i in range(hours):
        ts = now - _dt.timedelta(hours=hours - 1 - i)
        # Simulate diurnal traffic: lower at night (hours 0-6), peak mid-day
        hour_of_day = ts.hour
        base = 2000 + 3000 * math.sin(math.pi * (hour_of_day - 6) / 12) if 6 <= hour_of_day <= 18 else 800
        total = max(200, int(base + rng.randint(-300, 300)))
        # Error spike on one hour
        error_base = max(1, int(total * rng.uniform(0.002, 0.012)))
        error_requests = error_base * 8 if i == 14 else error_base
        entries.append({
            "hour": ts.isoformat() + "Z",
            "total_requests": total,
            "error_requests": min(error_requests, total),
        })
    return {"hours": entries}


def _mock_sla_history(days: int) -> dict[str, Any]:
    rng = _seed_rng(days + 3)
    today = _dt.date.today()
    result = []
    for i in range(days):
        d = today - _dt.timedelta(days=days - 1 - i)
        # One SLA violation day (day index 3)
        if i == 3:
            uptime = round(rng.uniform(99.2, 99.7), 2)
            avg_lat = round(rng.uniform(210, 280), 1)
            err_rate = round(rng.uniform(1.5, 2.8), 2)
            compliant = False
        else:
            uptime = round(rng.uniform(99.92, 99.99), 2)
            avg_lat = round(rng.uniform(55, 120), 1)
            err_rate = round(rng.uniform(0.05, 0.45), 2)
            compliant = True
        result.append({
            "date": d.isoformat(),
            "uptime_pct": uptime,
            "avg_latency_ms": avg_lat,
            "error_rate": err_rate,
            "compliant": compliant,
        })
    return {"days": result, "target_uptime_pct": 99.9}


def _mock_pipelines() -> list[dict[str, Any]]:
    rng = _seed_rng(99)
    pipelines = [
        ("audio-feature-extraction", "healthy"),
        ("image-preprocessing", "healthy"),
        ("clip-embedding-indexing", "degraded"),
        ("motion-analysis", "healthy"),
        ("multimodal-fusion", "healthy"),
    ]
    result = []
    for name, status in pipelines:
        total_runs = rng.randint(800, 3000)
        failed = rng.randint(2, 30) if status == "healthy" else rng.randint(60, 150)
        result.append({
            "id": name,
            "name": name.replace("-", " ").title(),
            "status": status,
            "total_runs_24h": total_runs,
            "failed_runs_24h": failed,
            "success_rate": round((total_runs - failed) / total_runs * 100, 2),
            "avg_duration_sec": round(rng.uniform(3.5, 45.0), 1),
            "last_run": (_dt.datetime.utcnow() - _dt.timedelta(minutes=rng.randint(1, 120))).isoformat() + "Z",
        })
    return result


def _mock_error_details(hours: int) -> list[dict[str, Any]]:
    rng = _seed_rng(hours + 5)
    now = _dt.datetime.utcnow()
    errors = [
        {
            "error_type": "TimeoutError",
            "message": "Upstream service did not respond within 30s",
            "severity": "warning",
            "count_24h": rng.randint(30, 80),
            "affected_endpoints": ["/api/search/vector", "/api/pipeline/run"],
        },
        {
            "error_type": "GPUMemoryError",
            "message": "CUDA out of memory during batch inference",
            "severity": "critical",
            "count_24h": rng.randint(5, 15),
            "affected_endpoints": ["/api/inference/batch", "/api/vision/embed"],
        },
        {
            "error_type": "ValidationError",
            "message": "Invalid audio sample rate: expected 16000, got 44100",
            "severity": "info",
            "count_24h": rng.randint(50, 200),
            "affected_endpoints": ["/api/audio/upload", "/api/audio/features"],
        },
        {
            "error_type": "ConnectionPoolExhausted",
            "message": "All database connections in use, request queued",
            "severity": "warning",
            "count_24h": rng.randint(10, 40),
            "affected_endpoints": ["/api/datasets/list", "/api/annotations/save"],
        },
        {
            "error_type": "ModelLoadError",
            "message": "Failed to load CLIP-ViT-L/14 checkpoint from registry",
            "severity": "critical",
            "count_24h": rng.randint(2, 8),
            "affected_endpoints": ["/api/vision/classify"],
        },
    ]
    for err in errors:
        daily_counts = []
        for d in range(7):
            day = (now - _dt.timedelta(days=6 - d)).strftime("%Y-%m-%d")
            daily_counts.append({"date": day, "count": rng.randint(0, err["count_24h"])})
        err["daily_counts"] = daily_counts
        # Add sample traces
        err["sample_traces"] = [
            {
                "trace_id": f"trace-{rng.randint(100000, 999999)}",
                "timestamp": (now - _dt.timedelta(minutes=rng.randint(5, 1400))).isoformat() + "Z",
                "duration_ms": round(rng.uniform(50, 5000), 1),
                "status_code": rng.choice([500, 502, 503, 504]) if err["severity"] != "info" else 422,
            }
            for _ in range(3)
        ]
    return errors

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
    range: Optional[str] = Query(None, description="Time range: 1h, 6h, 12h, 24h, 48h, 7d (overrides hours)"),
    db: AsyncSession = Depends(get_async_session),
):
    """Categorised error breakdown.

    When called with ``range`` (e.g. ``?range=24h``) returns detailed error
    stubs for the observability page.  When called with ``hours`` only,
    delegates to the original SREDashboardService taxonomy.
    """
    if range is not None:
        return _mock_error_details(_parse_range_hours(range))
    return await SREDashboardService.get_error_taxonomy(db, hours=hours)


@router.get("/queues")
async def queue_metrics():
    """Celery / task-queue metrics."""
    return await SREDashboardService.get_queue_metrics()


# ------------------------------------------------------------------
# Observability Page endpoints (mock stubs)
# ------------------------------------------------------------------


@router.get("/metrics")
async def observability_metrics(
    range: str = Query("24h", description="Time range: 1h, 6h, 12h, 24h, 48h, 7d"),
):
    """System overview metrics for the observability page."""
    return _mock_metrics(_parse_range_hours(range))


@router.get("/latency-history")
async def latency_history(
    range: str = Query("24h", description="Time range: 1h, 6h, 12h, 24h, 48h, 7d"),
):
    """Latency time-series with avg and p99 per hour."""
    return _mock_latency_history(_parse_range_hours(range))


@router.get("/request-volume")
async def request_volume(
    range: str = Query("24h", description="Time range: 1h, 6h, 12h, 24h, 48h, 7d"),
):
    """Hourly request volume with error breakdown."""
    return _mock_request_volume(_parse_range_hours(range))


@router.get("/sla-history")
async def sla_history(
    days: int = Query(7, ge=1, le=90, description="Number of days"),
):
    """Daily SLA compliance history."""
    return _mock_sla_history(days)


@router.get("/pipelines")
async def pipelines_overview():
    """Pipeline status and execution metrics."""
    return _mock_pipelines()



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
