"""ReviewOps routes — task management, assignments, review submissions."""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/reviewops", tags=["reviewops"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    asset_ids: list[str] = Field(default_factory=list)
    workspace_id: str | None = None


class TaskAssign(BaseModel):
    reviewer_id: str


class ReviewSubmit(BaseModel):
    verdict: str = Field(..., pattern="^(approved|rejected|needs_changes)$")
    comments: str = ""
    annotations: dict[str, Any] = Field(default_factory=dict)


class TaskDecision(BaseModel):
    """Body for PATCH /tasks/{id} — workspace review decision."""

    decision: Literal["approved", "rejected", "escalated"]
    notes: str | None = Field(None, max_length=500)
    flagged_annotations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_tasks: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/tasks")
async def create_task(body: TaskCreate) -> dict[str, Any]:
    tid = str(uuid.uuid4())
    task = {
        "id": tid,
        "title": body.title,
        "description": body.description,
        "asset_ids": body.asset_ids,
        "status": "pending",
        "reviewer_id": None,
        "review": None,
        "created_at": time.time(),
    }
    _tasks[tid] = task
    return task


@router.get("/tasks")
async def list_tasks(status: str | None = None) -> list[dict]:
    tasks = list(_tasks.values())
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return tasks


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return _tasks[task_id]


@router.post("/tasks/{task_id}/assign")
async def assign_task(task_id: str, body: TaskAssign) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    _tasks[task_id]["reviewer_id"] = body.reviewer_id
    _tasks[task_id]["status"] = "assigned"
    return _tasks[task_id]


@router.post("/tasks/{task_id}/review")
async def submit_review(task_id: str, body: ReviewSubmit) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    _tasks[task_id]["review"] = {
        "verdict": body.verdict,
        "comments": body.comments,
        "annotations": body.annotations,
        "submitted_at": time.time(),
    }
    _tasks[task_id]["status"] = "completed" if body.verdict == "approved" else "needs_changes"
    return _tasks[task_id]


@router.get("/tasks/{task_id}/status")
async def check_task_status(task_id: str) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = _tasks[task_id]
    return {"task_id": task_id, "status": task["status"], "completed": task["status"] == "completed"}


# ---------------------------------------------------------------------------
# Review Workspace stubs — GET task data, PATCH decision
# ---------------------------------------------------------------------------


@router.get("/tasks/{task_id}/data")
async def get_task_data(task_id: str) -> dict[str, Any]:
    """Return media + annotation data for the review workspace.

    Stub: returns synthetic data so the frontend can render immediately.
    Replace with real asset/annotation lookups once storage is wired up.
    """
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = _tasks[task_id]

    # Synthetic stub data keyed by a rough review-type heuristic
    annotations: list[dict[str, Any]] = [
        {
            "id": str(uuid.uuid4()),
            "label": "person",
            "confidence": 0.95,
            "bbox": {"x": 50, "y": 30, "width": 120, "height": 200},
            "flagged": False,
        },
        {
            "id": str(uuid.uuid4()),
            "label": "vehicle",
            "confidence": 0.82,
            "bbox": {"x": 300, "y": 150, "width": 180, "height": 100},
            "flagged": False,
        },
    ]

    dataset_sample: list[dict[str, Any]] = [
        {"row": 1, "text": "Sample text content", "label": "positive", "score": 0.91},
        {"row": 2, "text": "Another sample row", "label": "negative", "score": 0.45},
        {"row": 3, "text": "Third sample entry", "label": "neutral", "score": 0.67},
    ]

    model_prediction: dict[str, Any] = {
        "input": "A pedestrian crossing the street at a busy intersection.",
        "prediction": "pedestrian_crossing",
        "confidence": 0.88,
    }

    return {
        "media_url": None,  # Replace with real asset URL
        "media_type": None,
        "annotations": annotations,
        "dataset_sample": dataset_sample,
        "model_prediction": model_prediction,
    }


@router.patch("/tasks/{task_id}")
async def patch_task_decision(task_id: str, body: TaskDecision) -> dict[str, Any]:
    """Apply a review workspace decision (approve/reject/escalate).

    Updates the task status and records the decision. In production this
    should persist a Review row and trigger downstream workflows.
    """
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.decision == "rejected" and not body.notes:
        raise HTTPException(
            status_code=422,
            detail="Quality notes are required when rejecting a task",
        )

    status_map: dict[str, str] = {
        "approved": "completed",
        "rejected": "needs_changes",
        "escalated": "escalated",
    }

    task = _tasks[task_id]
    task["status"] = status_map[body.decision]
    task["review"] = {
        "decision": body.decision,
        "notes": body.notes,
        "flagged_annotations": body.flagged_annotations,
        "submitted_at": time.time(),
    }

    return task
