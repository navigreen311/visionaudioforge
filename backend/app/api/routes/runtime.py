"""Runtime Orchestrator API routes — GPU, routing, cost, quota, and caching."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.runtime.router import ModelRouter, ModelRouteConfig
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
async def get_cost_report(workspace_id: str, period: str = "monthly"):
    """Get cost report for a workspace."""
    report = _cost_controller.generate_cost_report(None, workspace_id, period=period)
    return report


@router.get("/quota/{workspace_id}")
async def get_quota_status(workspace_id: str):
    """Get current quota status for a workspace."""
    status = _cost_controller.check_quota(workspace_id)
    return status


@router.post("/quota")
async def set_quota(body: QuotaSetRequest):
    """Set daily inference quota for a workspace."""
    _cost_controller.set_quota(body.workspace_id, body.daily_limit)
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
