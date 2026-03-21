"""Pipeline API routes — create, list, validate, run, and inspect pipelines."""

from __future__ import annotations

import uuid
from datetime import datetime
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


class SuggestNextRequest(BaseModel):
    current_nodes: list[str]


class PipelineSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    definition: dict[str, Any] = Field(default_factory=dict)


class PipelineScheduleUpdate(BaseModel):
    cron: str | None = None
    enabled: bool = True
    timezone: str = "UTC"


# --------------------------------------------------------------------------
# Mock-data stubs for Pipeline page UI
# --------------------------------------------------------------------------

MOCK_PIPELINES = [
    {
        "id": "pipe_001",
        "name": "Audio Feature Extraction",
        "node_count": 4,
        "status": "active",
        "updated_at": "2026-03-19T14:30:00Z",
    },
    {
        "id": "pipe_002",
        "name": "Vision Preprocessing + CLIP Embedding",
        "node_count": 6,
        "status": "draft",
        "updated_at": "2026-03-18T09:15:00Z",
    },
    {
        "id": "pipe_003",
        "name": "Multimodal Fusion Pipeline",
        "node_count": 8,
        "status": "scheduled",
        "updated_at": "2026-03-17T22:45:00Z",
    },
]

MOCK_RUNS = [
    {
        "run_id": "run_001",
        "pipeline_id": "pipe_001",
        "pipeline_name": "Audio Feature Extraction",
        "status": "completed",
        "started_at": "2026-03-19T14:35:00Z",
        "finished_at": "2026-03-19T14:42:00Z",
        "nodes_completed": 4,
        "nodes_total": 4,
        "log": [
            {"timestamp": "2026-03-19T14:35:01Z", "node": "ingest", "level": "info", "message": "Loading audio files from /data/raw"},
            {"timestamp": "2026-03-19T14:36:10Z", "node": "normalize", "level": "info", "message": "Normalized 128 audio clips"},
            {"timestamp": "2026-03-19T14:38:45Z", "node": "extract_mfcc", "level": "info", "message": "Extracted 13 MFCCs per clip"},
            {"timestamp": "2026-03-19T14:42:00Z", "node": "export", "level": "info", "message": "Saved features to /data/processed/mfcc.npy"},
        ],
    },
    {
        "run_id": "run_002",
        "pipeline_id": "pipe_002",
        "pipeline_name": "Vision Preprocessing + CLIP Embedding",
        "status": "failed",
        "started_at": "2026-03-18T10:00:00Z",
        "finished_at": "2026-03-18T10:05:30Z",
        "nodes_completed": 3,
        "nodes_total": 6,
        "log": [
            {"timestamp": "2026-03-18T10:00:01Z", "node": "load_images", "level": "info", "message": "Loaded 256 images"},
            {"timestamp": "2026-03-18T10:02:00Z", "node": "resize", "level": "info", "message": "Resized to 224x224"},
            {"timestamp": "2026-03-18T10:03:30Z", "node": "color_convert", "level": "info", "message": "Converted BGR to RGB"},
            {"timestamp": "2026-03-18T10:05:30Z", "node": "clip_embed", "level": "error", "message": "CUDA out of memory — reduce batch size"},
        ],
    },
    {
        "run_id": "run_003",
        "pipeline_id": "pipe_003",
        "pipeline_name": "Multimodal Fusion Pipeline",
        "status": "running",
        "started_at": "2026-03-19T15:00:00Z",
        "finished_at": None,
        "nodes_completed": 5,
        "nodes_total": 8,
        "log": [
            {"timestamp": "2026-03-19T15:00:01Z", "node": "audio_ingest", "level": "info", "message": "Ingested 64 audio samples"},
            {"timestamp": "2026-03-19T15:01:30Z", "node": "vision_ingest", "level": "info", "message": "Ingested 64 image samples"},
            {"timestamp": "2026-03-19T15:03:00Z", "node": "audio_features", "level": "info", "message": "Extracted MEL spectrograms"},
            {"timestamp": "2026-03-19T15:05:00Z", "node": "vision_features", "level": "info", "message": "Extracted CLIP embeddings"},
            {"timestamp": "2026-03-19T15:07:00Z", "node": "align", "level": "info", "message": "Temporal alignment complete"},
        ],
    },
]


@router.get("/pipeline/list")
async def list_pipelines_mock() -> list[dict[str, Any]]:
    """Return mock pipeline list for Pipeline page UI."""
    return MOCK_PIPELINES


@router.post("/pipeline/save")
async def save_pipeline_mock(body: PipelineSaveRequest) -> dict[str, Any]:
    """Accept a pipeline definition and return a draft stub."""
    return {
        "id": f"pipe_{uuid.uuid4().hex[:6]}",
        "name": body.name,
        "status": "draft",
    }


@router.patch("/pipeline/{pipeline_id}/schedule")
async def update_pipeline_schedule(
    pipeline_id: str,
    body: PipelineScheduleUpdate,
) -> dict[str, Any]:
    """Accept schedule config and return the updated pipeline stub."""
    return {
        "id": pipeline_id,
        "name": next(
            (p["name"] for p in MOCK_PIPELINES if p["id"] == pipeline_id),
            "Unknown Pipeline",
        ),
        "status": "scheduled" if body.enabled else "draft",
        "schedule": {
            "cron": body.cron,
            "enabled": body.enabled,
            "timezone": body.timezone,
        },
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.post("/pipeline/run")
async def run_pipeline_mock() -> dict[str, Any]:
    """Start a mock pipeline run and return a run stub."""
    return {"run_id": "run_001", "status": "running"}


@router.get("/pipeline/runs/{run_id}/status")
async def get_run_status(run_id: str) -> dict[str, Any]:
    """Return mock status for a specific pipeline run."""
    run = next((r for r in MOCK_RUNS if r["run_id"] == run_id), None)
    if run:
        return {
            "run_id": run["run_id"],
            "status": run["status"],
            "nodes_completed": run["nodes_completed"],
            "nodes_total": run["nodes_total"],
            "current_node": None if run["status"] == "completed" else run["log"][-1]["node"],
        }
    # Default fallback for unknown run_id
    return {
        "run_id": run_id,
        "status": "completed",
        "nodes_completed": 5,
        "nodes_total": 5,
        "current_node": None,
    }


@router.get("/pipeline/runs")
async def list_pipeline_runs_mock() -> list[dict[str, Any]]:
    """Return mock run history for Pipeline page UI."""
    return MOCK_RUNS


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
