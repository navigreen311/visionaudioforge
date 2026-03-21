"""Pipeline API routes — create, list, validate, run, and inspect pipelines."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.pipeline import Pipeline, PipelineRun
from app.schemas.common import PaginatedResponse
from app.schemas.pipeline import (
    NodeTypeInfo,
    PipelineCreate,
    PipelineRead,
    PipelineRunRead,
    PipelineRunStart,
    PipelineValidate,
    ValidationResult,
)
from app.services.pipeline.engine import PipelineEngine
from app.services.pipeline.nl_generator import NLPipelineGenerator
from app.services.pipeline.nodes import NODE_REGISTRY, get_node
from app.services.pipeline.scheduler import PipelineScheduler
from app.services.pipeline.templates import PIPELINE_TEMPLATES, get_template, list_templates

router = APIRouter(prefix="/api", tags=["pipeline"])

engine = PipelineEngine()
nl_generator = NLPipelineGenerator()
scheduler = PipelineScheduler()


# -- Request/response models for new endpoints --------------------------------

class GenerateRequest(BaseModel):
    description: str = Field(..., min_length=3, max_length=1000)


class ScheduleRequest(BaseModel):
    pipeline_id: str
    cron: str


class SchedulePatchRequest(BaseModel):
    enabled: bool = True
    cron: str
    timezone: str = "UTC"


class PipelineRunRequest(BaseModel):
    pipeline_id: str
    rerun_of: str | None = None


class SuggestNextRequest(BaseModel):
    current_nodes: list[str]


# --------------------------------------------------------------------------
# GET /api/pipeline/nodes — catalogue of available node types
# --------------------------------------------------------------------------

@router.get("/pipeline/nodes", response_model=list[NodeTypeInfo])
async def list_node_types() -> list[dict[str, Any]]:
    """Return all registered node types with their input/output schemas."""
    result = []
    for type_key, cls in NODE_REGISTRY.items():
        instance = cls()
        result.append({
            "type": type_key,
            "category": instance.category,
            "description": instance.description,
            "inputs": instance.input_schema,
            "outputs": instance.output_schema,
        })
    return result


# --------------------------------------------------------------------------
# POST /api/pipeline/validate
# --------------------------------------------------------------------------

@router.post("/pipeline/validate", response_model=ValidationResult)
async def validate_pipeline(body: PipelineValidate) -> dict:
    """Validate a pipeline definition without saving."""
    return engine.validate_pipeline(body.definition)


# --------------------------------------------------------------------------
# POST /api/pipeline/create
# --------------------------------------------------------------------------

@router.post("/pipeline/create", response_model=PipelineRead, status_code=201)
async def create_pipeline(
    body: PipelineCreate,
    db: AsyncSession = Depends(get_db),
) -> Pipeline:
    """Create a new pipeline."""
    validation = engine.validate_pipeline(body.definition)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail=validation["errors"])

    pipeline = Pipeline(
        name=body.name,
        description=body.description,
        definition=body.definition,
        workspace_id=body.workspace_id,
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


# --------------------------------------------------------------------------
# GET /api/pipelines
# --------------------------------------------------------------------------

@router.get("/pipelines", response_model=PaginatedResponse)
async def list_pipelines(
    workspace_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List pipelines, optionally filtered by workspace."""
    query = select(Pipeline)
    count_query = select(func.count(Pipeline.id))

    if workspace_id:
        query = query.where(Pipeline.workspace_id == workspace_id)
        count_query = count_query.where(Pipeline.workspace_id == workspace_id)

    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, -(-total // page_size))

    query = query.order_by(Pipeline.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [PipelineRead.model_validate(p) for p in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# --------------------------------------------------------------------------
# GET /api/pipelines/{pipeline_id}
# --------------------------------------------------------------------------

@router.get("/pipelines/{pipeline_id}", response_model=PipelineRead)
async def get_pipeline(
    pipeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Pipeline:
    """Get a single pipeline by ID."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


# --------------------------------------------------------------------------
# POST /api/pipeline/run/{pipeline_id}
# --------------------------------------------------------------------------

@router.post("/pipeline/run/{pipeline_id}", response_model=PipelineRunStart)
async def run_pipeline(
    pipeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a pipeline run — dispatches a Celery task."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    run = PipelineRun(pipeline_id=pipeline_id, status="pending")
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Dispatch Celery task (best-effort; won't fail the request if broker is down)
    try:
        from app.tasks.pipeline import run_pipeline_task

        run_pipeline_task.delay(str(pipeline_id), pipeline.definition)
    except Exception:
        pass  # Task dispatch is fire-and-forget in dev mode

    return {"run_id": run.id, "status": "pending"}


# --------------------------------------------------------------------------
# GET /api/pipeline/runs/{run_id}
# --------------------------------------------------------------------------

@router.get("/pipeline/runs/{run_id}", response_model=PipelineRunRead)
async def get_pipeline_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PipelineRun:
    """Get a pipeline run by ID."""
    result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return run


# --------------------------------------------------------------------------
# POST /api/pipeline/generate — NL-to-pipeline generation
# --------------------------------------------------------------------------

@router.post("/pipeline/generate")
async def generate_pipeline(body: GenerateRequest) -> dict:
    """Generate a pipeline definition from a natural language description."""
    definition = await nl_generator.generate_from_description(body.description)
    return {"definition": definition, "description": body.description}


# --------------------------------------------------------------------------
# GET /api/pipeline/templates — list all templates
# --------------------------------------------------------------------------

@router.get("/pipeline/templates")
async def get_templates() -> list[dict]:
    """Return all pre-built pipeline templates."""
    return list_templates()


# --------------------------------------------------------------------------
# GET /api/pipeline/templates/{name} — get specific template
# --------------------------------------------------------------------------

@router.get("/pipeline/templates/{name}")
async def get_template_by_name(name: str) -> dict:
    """Return a specific pipeline template by key."""
    template = get_template(name)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return {"key": name, **template}


# --------------------------------------------------------------------------
# POST /api/pipeline/schedule — schedule a pipeline
# --------------------------------------------------------------------------

@router.post("/pipeline/schedule")
async def schedule_pipeline(body: ScheduleRequest) -> dict:
    """Create a cron schedule for a pipeline."""
    try:
        result = await scheduler.schedule(body.pipeline_id, body.cron)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result


# --------------------------------------------------------------------------
# GET /api/pipeline/schedules — list all schedules
# --------------------------------------------------------------------------

@router.get("/pipeline/schedules")
async def get_schedules(workspace_id: str | None = Query(None)) -> list[dict]:
    """Return all active pipeline schedules."""
    return await scheduler.list_schedules(workspace_id)


# --------------------------------------------------------------------------
# POST /api/pipeline/suggest-next — suggest next nodes
# --------------------------------------------------------------------------

@router.post("/pipeline/suggest-next")
async def suggest_next_nodes(body: SuggestNextRequest) -> dict:
    """Suggest next nodes based on current pipeline composition."""
    suggestions = await nl_generator.suggest_next_nodes(body.current_nodes)
    return {"suggestions": suggestions}


# --------------------------------------------------------------------------
# PATCH /api/pipeline/{pipeline_id}/schedule — update schedule for a pipeline
# --------------------------------------------------------------------------

@router.patch("/pipeline/{pipeline_id}/schedule")
async def update_pipeline_schedule(
    pipeline_id: uuid.UUID,
    body: SchedulePatchRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create or update a cron schedule for a specific pipeline."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    try:
        schedule_result = await scheduler.schedule(str(pipeline_id), body.cron)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "pipeline_id": str(pipeline_id),
        "enabled": body.enabled,
        "cron": body.cron,
        "timezone": body.timezone,
        **schedule_result,
    }


# --------------------------------------------------------------------------
# POST /api/pipeline/run — start a pipeline run (accepts body with pipeline_id)
# --------------------------------------------------------------------------

@router.post("/pipeline/run")
async def start_pipeline_run(
    body: PipelineRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start a new pipeline run from a JSON body (supports re-runs)."""
    pid = uuid.UUID(body.pipeline_id)
    result = await db.execute(select(Pipeline).where(Pipeline.id == pid))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    run = PipelineRun(pipeline_id=pid, status="pending")
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Fire-and-forget task dispatch
    try:
        from app.tasks.pipeline import run_pipeline_task
        run_pipeline_task.delay(str(pid), pipeline.definition)
    except Exception:
        pass

    return {"run_id": str(run.id), "status": "pending", "rerun_of": body.rerun_of}


# --------------------------------------------------------------------------
# GET /api/pipeline/runs/{run_id}/status — live run status with per-node states
# --------------------------------------------------------------------------

@router.get("/pipeline/runs/{run_id}/status")
async def get_run_status(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current run status with per-node progress (stub)."""
    result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    # In a real implementation, node states would come from the task runner.
    # For now, return a stub based on the run's overall status.
    pipeline_result = await db.execute(
        select(Pipeline).where(Pipeline.id == run.pipeline_id)
    )
    pipeline = pipeline_result.scalar_one_or_none()
    definition = pipeline.definition if pipeline else {}
    node_defs: list[dict[str, Any]] = definition.get("nodes", [])

    status_str = run.status.value if hasattr(run.status, "value") else str(run.status)

    node_states = []
    for i, node_def in enumerate(node_defs):
        if status_str == "completed":
            node_status = "completed"
        elif status_str == "failed":
            node_status = "completed" if i < len(node_defs) - 1 else "failed"
        elif status_str == "running":
            node_status = "completed" if i == 0 else ("running" if i == 1 else "pending")
        else:
            node_status = "pending"

        node_states.append({
            "node_id": node_def.get("id", f"node-{i}"),
            "node_name": node_def.get("type", f"Node {i + 1}"),
            "status": node_status,
        })

    elapsed_ms = 0
    if run.started_at and run.finished_at:
        elapsed_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

    return {
        "run_id": str(run.id),
        "pipeline_status": status_str,
        "nodes": node_states,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "elapsed_ms": elapsed_ms,
    }


# --------------------------------------------------------------------------
# GET /api/pipeline/runs — list runs, optionally filtered by pipeline_id
# --------------------------------------------------------------------------

@router.get("/pipeline/runs")
async def list_pipeline_runs(
    pipeline_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List pipeline runs with summary data for the RunHistory table."""
    query = select(PipelineRun).order_by(PipelineRun.id.desc())
    if pipeline_id:
        query = query.where(PipelineRun.pipeline_id == pipeline_id)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    runs = result.scalars().all()

    items = []
    for idx, run in enumerate(runs):
        status_str = run.status.value if hasattr(run.status, "value") else str(run.status)

        duration_ms = None
        if run.started_at and run.finished_at:
            duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

        # Derive node counts from pipeline definition
        pipeline_result = await db.execute(
            select(Pipeline).where(Pipeline.id == run.pipeline_id)
        )
        pipeline = pipeline_result.scalar_one_or_none()
        nodes_total = len((pipeline.definition or {}).get("nodes", [])) if pipeline else 0
        nodes_executed = nodes_total if status_str == "completed" else 0

        items.append({
            "id": str(run.id),
            "run_number": idx + 1,
            "status": status_str,
            "started_at": run.started_at.isoformat() if run.started_at else "",
            "duration_ms": duration_ms,
            "nodes_executed": nodes_executed,
            "nodes_total": nodes_total,
            "output_summary": None,
            "logs": [],
        })

    return items
