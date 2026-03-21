"""ReviewOps routes — task management, assignments, review submissions."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

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


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_tasks: dict[str, dict] = {}

# Mock reviewers
_REVIEWERS = [
    {"id": "rev-001", "name": "Alice Chen", "avatar": None},
    {"id": "rev-002", "name": "Bob Martinez", "avatar": None},
    {"id": "rev-003", "name": "Carol Singh", "avatar": None},
    {"id": "rev-004", "name": "Dan Okafor", "avatar": None},
]

# ---------------------------------------------------------------------------
# Seed mock tasks (8 tasks for development)
# ---------------------------------------------------------------------------

def _seed_mock_tasks() -> None:
    """Populate the in-memory store with 8 realistic mock tasks."""
    if _tasks:
        return
    now = datetime.now(timezone.utc)
    templates = [
        ("Verify bounding boxes for batch #1204", "annotation_qa", "critical", "pending", None, 0.5),
        ("Review detection model output v3.2", "detection_verify", "high", "assigned", "rev-001", 2.0),
        ("QA edge-case low-light frames", "edge_case", "high", "in_review", "rev-002", 3.5),
        ("Validate safety labels for NSFW filter", "safety_review", "critical", "pending", None, 1.0),
        ("Check audio-visual sync annotations", "annotation_qa", "normal", "assigned", "rev-003", 6.0),
        ("Review data quality for dataset v8", "data_quality", "normal", "in_review", "rev-004", 8.0),
        ("Verify model output confidence scores", "model_output", "low", "completed", "rev-001", -2.0),
        ("Escalated: mislabeled traffic signs", "detection_verify", "critical", "escalated", "rev-002", -1.0),
    ]
    for title, rtype, priority, status, assigned, hours_left in templates:
        tid = str(uuid.uuid4())
        _tasks[tid] = {
            "task_id": tid,
            "title": title,
            "review_type": rtype,
            "priority": priority,
            "status": status,
            "sla_deadline": (now + timedelta(hours=hours_left)).isoformat(),
            "assigned_to": assigned,
            "reviews_count": 1 if status in ("in_review", "completed") else 0,
            "required_reviews": 2,
        }


_seed_mock_tasks()


# ---------------------------------------------------------------------------
# GET /stats — aggregated stat cards
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats(
    workspace_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
) -> dict[str, Any]:
    """Return aggregated stats for the ReviewOps dashboard cards."""
    all_tasks = list(_tasks.values())
    now = datetime.now(timezone.utc)

    pending_count = sum(1 for t in all_tasks if t["status"] == "pending")
    in_review_count = sum(1 for t in all_tasks if t["status"] in ("assigned", "in_review"))
    completed_today_count = sum(1 for t in all_tasks if t["status"] == "completed")
    overdue_count = sum(
        1
        for t in all_tasks
        if t["status"] not in ("completed",)
        and datetime.fromisoformat(t["sla_deadline"]) < now
    )

    return {
        "pending": {"label": "Pending", "count": pending_count, "trend": 12},
        "in_review": {"label": "In Review", "count": in_review_count, "trend": -5},
        "completed_today": {"label": "Completed Today", "count": completed_today_count, "trend": 8},
        "overdue": {"label": "Overdue", "count": overdue_count, "trend": 0},
    }


# ---------------------------------------------------------------------------
# GET /reviewers — list available reviewers
# ---------------------------------------------------------------------------

@router.get("/reviewers")
async def list_reviewers(
    workspace_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
) -> list[dict[str, Any]]:
    """Return the list of available reviewers."""
    return _REVIEWERS


# ---------------------------------------------------------------------------
# POST /auto-assign — auto-assign pending tasks
# ---------------------------------------------------------------------------

@router.post("/auto-assign")
async def auto_assign(
    workspace_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
) -> dict[str, Any]:
    """Round-robin assign all pending tasks to available reviewers."""
    pending = [t for t in _tasks.values() if t["status"] == "pending"]
    assigned_count = 0
    for i, task in enumerate(pending):
        reviewer = _REVIEWERS[i % len(_REVIEWERS)]
        task["assigned_to"] = reviewer["id"]
        task["status"] = "assigned"
        assigned_count += 1
    return {"assigned_count": assigned_count, "message": f"Assigned {assigned_count} tasks"}


# ---------------------------------------------------------------------------
# Original endpoints (updated to use seeded tasks)
# ---------------------------------------------------------------------------

@router.post("/tasks")
async def create_task(body: TaskCreate) -> dict[str, Any]:
    tid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    task = {
        "task_id": tid,
        "title": body.title,
        "description": body.description,
        "review_type": "annotation_qa",
        "priority": "normal",
        "status": "pending",
        "sla_deadline": (now + timedelta(hours=4)).isoformat(),
        "assigned_to": None,
        "reviews_count": 0,
        "required_reviews": 2,
    }
    _tasks[tid] = task
    return task


@router.get("/tasks")
async def list_tasks(
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    workspace_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
) -> list[dict[str, Any]]:
    tasks = list(_tasks.values())
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if priority:
        tasks = [t for t in tasks if t.get("priority") == priority]
    if assignee:
        tasks = [t for t in tasks if t.get("assigned_to") == assignee]
    return tasks


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return _tasks[task_id]


@router.post("/tasks/{task_id}/assign")
async def assign_task(task_id: str, body: TaskAssign) -> dict[str, Any]:
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    _tasks[task_id]["assigned_to"] = body.reviewer_id
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
