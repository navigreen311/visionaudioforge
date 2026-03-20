"""Celery task for asynchronous pipeline execution."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.services.pipeline.engine import PipelineEngine


@celery_app.task(name="run_pipeline_task", bind=True, max_retries=1)
def run_pipeline_task(self, pipeline_id: str, definition: dict) -> dict:
    """Execute a pipeline definition asynchronously via Celery.

    In a full implementation this would:
    1. Load the pipeline from the DB by *pipeline_id*.
    2. Execute via ``PipelineEngine``.
    3. Persist a ``PipelineRun`` row with results.

    For now it accepts the definition directly so the task is self-contained.
    """
    engine = PipelineEngine()
    run_id = str(uuid.uuid4())

    try:
        result = asyncio.run(engine.execute_pipeline(definition))
        # Serialise numpy arrays etc. for JSON storage
        node_results = _serialise(result.get("node_results", {}))
        return {
            "run_id": run_id,
            "pipeline_id": pipeline_id,
            "status": result["status"],
            "node_results": node_results,
            "duration_ms": result["duration_ms"],
            "errors": result["errors"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "run_id": run_id,
            "pipeline_id": pipeline_id,
            "status": "failed",
            "errors": [str(exc)],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }


def _serialise(obj):
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
