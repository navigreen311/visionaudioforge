"""Runtime Orchestrator API routes - GPU, routing, cost, quota, and caching."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.services.runtime.router import ModelRouter, ModelRouteConfig

logger = logging.getLogger(__name__)
from app.services.runtime.gpu_scheduler import GPUScheduler
from app.services.runtime.cost_control import CostController
from app.services.runtime.cache import InferenceCache

router = APIRouter(prefix="/api/runtime", tags=["runtime"])

# ---------------------------------------------------------------------------
# Singleton service instances
# ---------------------------------------------------------------------------
_model_router = ModelRouter()
_gpu_scheduler = GPUScheduler()
_cost_controller = CostController()
_inference_cache = InferenceCache()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RouteRequest(BaseModel):
    request_type: str = "inference"
    constraints: dict | None = None


class QuotaSetRequest(BaseModel):
    workspace_id: str
    daily_limit: int = Field(ge=1)


# ---------------------------------------------------------------------------
# GPU routes
# ---------------------------------------------------------------------------

@router.get("/gpu")
async def gpu_status():
    """Return GPU device information."""
    devices = _gpu_scheduler.get_gpu_status()
    return {"devices": devices}


# ---------------------------------------------------------------------------
# Model routing
# ---------------------------------------------------------------------------

@router.post("/route")
async def route_model(body: RouteRequest):
    """Select the best model for a request based on constraints."""
    result = _model_router.route(body.request_type, body.constraints)
    return result


# ---------------------------------------------------------------------------
# Cost & Quota
# ---------------------------------------------------------------------------

@router.get("/cost/{workspace_id}")
async def get_cost_report(
    workspace_id: str,
    period: str = "monthly",
    db: AsyncSession = Depends(get_async_session),
):
    """Get cost report for a workspace."""
    return await _cost_controller.generate_cost_report(db, workspace_id, period=period)


@router.get("/quota/{workspace_id}")
async def get_quota_status(
    workspace_id: str,
    db: AsyncSession = Depends(get_async_session),
):
    """Get current quota status for a workspace."""
    return await _cost_controller.check_quota(db, workspace_id)


@router.post("/quota")
async def set_quota(
    body: QuotaSetRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Set daily inference quota for a workspace."""
    await _cost_controller.set_quota(db, body.workspace_id, body.daily_limit)
    return {"workspace_id": body.workspace_id, "daily_limit": body.daily_limit, "status": "set"}


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

@router.get("/cache/stats")
async def cache_stats():
    """Return inference cache statistics."""
    stats = await _inference_cache.get_cache_stats()
    return stats


@router.post("/cache/clear")
async def cache_clear(model_id: str | None = None):
    """Clear inference cache (all or for a specific model)."""
    count = await _inference_cache.invalidate(model_id)
    return {"cleared": count}


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

@router.get("/schedule")
async def current_schedule():
    """Return current job queue."""
    queue = _gpu_scheduler.get_queue()
    return {"queue": queue, "total_jobs": len(queue)}


# ---------------------------------------------------------------------------
# System metrics
# ---------------------------------------------------------------------------

class RuntimeMetricsResponse(BaseModel):
    """Resource-usage percentages (0-100) consumed by the dashboard gauges."""

    # Optional on purpose: null means "not measured on this host", which the
    # console renders as unknown. A gauge showing a plausible number nobody
    # measured is worse than a blank one.
    gpu: float | None = Field(default=None, ge=0, le=100, description="GPU utilisation %")
    cpu: float | None = Field(default=None, ge=0, le=100, description="CPU utilisation %")
    storage: float | None = Field(default=None, ge=0, le=100, description="Storage utilisation %")


@router.get("/metrics", response_model=RuntimeMetricsResponse)
async def runtime_metrics():
    """Host CPU, GPU and disk utilisation as percentages.

    The fallback used to be a hardcoded 12% CPU and 4.8% storage - the latter
    derived from the same invented "2.4 GB of 50" the assets page used to show.
    `psutil` was never a declared dependency, so that fallback was not an edge
    case: it was the only path this endpoint ever took.

    psutil is now a real requirement. If it is genuinely unavailable the values
    are reported as null, which the console can render as "unknown" - a gauge
    showing a plausible number nobody measured is worse than a blank one.
    """
    try:
        import psutil
    except ImportError:
        logger.warning("psutil is unavailable; reporting unknown utilisation")
        return RuntimeMetricsResponse(cpu=None, gpu=None, storage=None)

    cpu_pct = psutil.cpu_percent(interval=0.1)
    disk = psutil.disk_usage("/")
    storage_pct = round(disk.used / disk.total * 100, 1) if disk.total else None

    # No GPU telemetry is wired up. None, not zero: zero means "idle".
    return RuntimeMetricsResponse(
        cpu=round(cpu_pct, 1), gpu=None, storage=storage_pct
    )


