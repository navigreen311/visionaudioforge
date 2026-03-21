"""Observability routes — SRE dashboard, SLA, alert fatigue analytics."""

import random
import uuid as _uuid
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
# OB5 — Per-pipeline breakdown (mock data)
# ------------------------------------------------------------------

_PIPELINE_NAMES = [
    "Vision Detect",
    "Audio Transform",
    "Feature Extraction",
    "Model Training",
    "Data Ingestion",
    "Export Pipeline",
]

_PIPELINE_STATUSES = ["running", "healthy", "degraded", "failed", "inactive"]


@router.get("/pipelines")
async def list_pipelines() -> dict:
    """Return per-pipeline health rows for the Pipeline Health Table (OB5)."""
    now = datetime.now(timezone.utc)
    pipelines: list[dict] = []
    for name in _PIPELINE_NAMES:
        status = random.choice(_PIPELINE_STATUSES)
        runs_24h = random.randint(0, 320)
        success_rate = round(random.uniform(0.7, 1.0), 4) if runs_24h > 0 else 0.0
        pipelines.append(
            {
                "id": str(_uuid.uuid5(_uuid.NAMESPACE_DNS, name)),
                "name": name,
                "status": status,
                "runs24h": runs_24h,
                "successRate": success_rate,
                "avgDurationMs": round(random.uniform(800, 30000), 2),
                "lastRun": (
                    now - timedelta(minutes=random.randint(1, 1440))
                ).isoformat(),
                "enabled": status != "inactive",
            }
        )
    return {"pipelines": pipelines}


# ------------------------------------------------------------------
# OB6 — Error taxonomy rows (mock data)
# ------------------------------------------------------------------

_ERROR_TYPES = [
    {
        "errorType": "ValidationError",
        "endpoints": ["/api/vision/detect", "/api/pipeline/run"],
        "stack": 'File "app/api/routes/vision.py", line 42, in detect\n    raise ValidationError("Invalid image format")',
    },
    {
        "errorType": "TimeoutError",
        "endpoints": ["/api/audio/transform"],
        "stack": 'File "app/services/audio.py", line 118, in transform\n    raise TimeoutError("Upstream model timeout after 30s")',
    },
    {
        "errorType": "InternalServerError",
        "endpoints": ["/api/pipeline/run", "/api/vision/detect"],
        "stack": 'File "app/core/runner.py", line 55, in execute\n    raise RuntimeError("Unexpected null tensor")',
    },
    {
        "errorType": "NotFoundError",
        "endpoints": ["/api/assets/download"],
        "stack": 'File "app/api/routes/assets.py", line 28, in download\n    raise HTTPException(404, "Asset not found")',
    },
    {
        "errorType": "RateLimitExceeded",
        "endpoints": ["/api/search/query", "/api/agents/chat"],
        "stack": 'File "app/middleware/rate_limit.py", line 14, in __call__\n    raise RateLimitExceeded("429 Too Many Requests")',
    },
]


@router.get("/errors/taxonomy")
async def error_taxonomy_rows(
    hours: int = Query(24, ge=1, le=720),
) -> dict:
    """Return detailed error taxonomy rows for the Error Taxonomy Table (OB6)."""
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for et in _ERROR_TYPES:
        count = random.randint(1, 45)
        rows.append(
            {
                "id": str(_uuid.uuid5(_uuid.NAMESPACE_DNS, et["errorType"])),
                "errorType": et["errorType"],
                "count": count,
                "lastSeen": (
                    now - timedelta(minutes=random.randint(1, hours * 60))
                ).isoformat(),
                "trend": {
                    "values": [random.randint(0, count) for _ in range(7)],
                },
                "affectedEndpoints": et["endpoints"],
                "detail": {
                    "traceIds": [str(_uuid.uuid4()) for _ in range(random.randint(1, 4))],
                    "stackExcerpt": et["stack"],
                },
            }
        )
    rows.sort(key=lambda r: r["count"], reverse=True)
    return {"errors": rows}


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
