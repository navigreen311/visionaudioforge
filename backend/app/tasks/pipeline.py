"""Celery task for asynchronous pipeline execution.

The task owns the run's lifecycle: it is handed the ``PipelineRun`` row the
request already created and moves it through running → completed/failed,
persisting results. Previously it invented its own run id and returned a dict
nobody stored, so the row the console polls stayed ``pending`` forever no
matter what the worker did.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.config import settings
from app.models.pipeline import Pipeline, PipelineRun, PipelineRunStatus
from app.services.pipeline.engine import PipelineEngine

logger = logging.getLogger(__name__)


def _session_factory() -> async_sessionmaker[AsyncSession]:
    """Build a session factory for this worker process.

    The API's engine belongs to the API's event loop; a Celery worker runs its
    own loop per task, so it makes its own short-lived engine.
    """
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="run_pipeline_task", bind=True, max_retries=1)
def run_pipeline_task(
    self,
    run_id: str,
    pipeline_id: str,
    definition: dict | None = None,
) -> dict:
    """Execute a pipeline run and record the outcome against its row."""
    return asyncio.run(_run_pipeline(run_id, pipeline_id, definition))


async def _run_pipeline(
    run_id: str,
    pipeline_id: str,
    definition: dict | None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> dict:
    """Run the pipeline and record the outcome.

    ``session_factory`` exists so a caller that already has a configured
    engine — a test, or an in-process runner — can supply it instead of the
    worker building its own from settings.
    """
    factory = session_factory or _session_factory()
    engine = PipelineEngine()
    started_at = datetime.now(timezone.utc)

    async with factory() as db:
        run = await _load_run(db, run_id)

        if definition is None:
            definition = await _load_definition(db, pipeline_id)

        if run is not None:
            run.status = PipelineRunStatus.running
            run.started_at = started_at
            await db.commit()

        try:
            result = await engine.execute_pipeline(definition or {})
            node_results = _serialise(result.get("node_results", {}))
            succeeded = result.get("status") != "failed"
            errors = result.get("errors") or []
            duration_ms = result.get("duration_ms")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Pipeline run %s failed", run_id)
            node_results = {}
            succeeded = False
            errors = [str(exc)]
            duration_ms = int(
                (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
            )

        finished_at = datetime.now(timezone.utc)
        payload = {
            "run_id": run_id,
            "pipeline_id": pipeline_id,
            "status": "completed" if succeeded else "failed",
            "node_results": node_results,
            "duration_ms": duration_ms,
            "errors": errors,
            "completed_at": finished_at.isoformat(),
        }

        if run is not None:
            run.status = (
                PipelineRunStatus.completed if succeeded else PipelineRunStatus.failed
            )
            run.finished_at = finished_at
            run.results = payload
            await db.commit()

        return payload


async def _load_run(db: AsyncSession, run_id: str) -> PipelineRun | None:
    try:
        key = uuid.UUID(str(run_id))
    except (ValueError, AttributeError, TypeError):
        logger.warning("Pipeline task got an unusable run id: %r", run_id)
        return None

    result = await db.execute(select(PipelineRun).where(PipelineRun.id == key))
    run = result.scalar_one_or_none()
    if run is None:
        logger.warning("Pipeline run %s no longer exists", run_id)
    return run


async def _load_definition(db: AsyncSession, pipeline_id: str) -> dict:
    try:
        key = uuid.UUID(str(pipeline_id))
    except (ValueError, AttributeError, TypeError):
        return {}

    result = await db.execute(select(Pipeline).where(Pipeline.id == key))
    pipeline = result.scalar_one_or_none()
    return (pipeline.definition or {}) if pipeline else {}


def _serialise(obj: Any) -> Any:
    """Best-effort JSON-safe serialisation of pipeline outputs."""
    import numpy as np

    if isinstance(obj, dict):
        return {k: _serialise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialise(i) for i in obj]
    if isinstance(obj, np.ndarray):
        if obj.size < 50:
            return obj.tolist()
        return f"<ndarray shape={obj.shape} dtype={obj.dtype}>"
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    return obj
