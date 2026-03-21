"""ReviewOps routes — task management, assignments, review submissions."""

from __future__ import annotations

import time
import uuid
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
    tasks = list(_tasks.values()) + _MOCK_TASKS
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
# Schemas (batch-6 additions)
# ---------------------------------------------------------------------------

class TaskPatch(BaseModel):
    status: str | None = None
    decision: str | None = None
    note: str | None = None


class ShiftCreate(BaseModel):
    name: str
    reviewer_ids: list[str] = Field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    timezone: str = "UTC"


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_TASKS: list[dict[str, Any]] = [
    {"id": "task-001", "name": "Verify bounding boxes – batch 12", "type": "annotation_review", "priority": "high", "status": "pending", "assignee": None, "sla_deadline": "2026-03-21T18:00:00Z"},
    {"id": "task-002", "name": "Audio segmentation QA", "type": "qa_check", "priority": "medium", "status": "in_review", "assignee": "reviewer-1", "sla_deadline": "2026-03-21T20:00:00Z"},
    {"id": "task-003", "name": "Label consistency – driving dataset", "type": "consistency_check", "priority": "high", "status": "pending", "assignee": None, "sla_deadline": "2026-03-22T12:00:00Z"},
    {"id": "task-004", "name": "Edge-case frames review", "type": "annotation_review", "priority": "critical", "status": "overdue", "assignee": "reviewer-2", "sla_deadline": "2026-03-20T10:00:00Z"},
    {"id": "task-005", "name": "Speech transcription validation", "type": "qa_check", "priority": "low", "status": "completed", "assignee": "reviewer-3", "sla_deadline": "2026-03-21T14:00:00Z"},
    {"id": "task-006", "name": "Polygon mask accuracy", "type": "annotation_review", "priority": "medium", "status": "pending", "assignee": None, "sla_deadline": "2026-03-22T09:00:00Z"},
    {"id": "task-007", "name": "Multi-speaker diarization check", "type": "qa_check", "priority": "high", "status": "in_review", "assignee": "reviewer-1", "sla_deadline": "2026-03-21T23:00:00Z"},
    {"id": "task-008", "name": "Semantic segmentation review", "type": "annotation_review", "priority": "medium", "status": "pending", "assignee": None, "sla_deadline": "2026-03-22T16:00:00Z"},
]

_MOCK_REVIEWERS: list[dict[str, Any]] = [
    {"id": "reviewer-1", "name": "Alice Chen", "email": "alice@example.com", "role": "senior_reviewer", "active_tasks": 2, "avg_review_time_min": 8.4, "accuracy": 0.96},
    {"id": "reviewer-2", "name": "Bob Martinez", "email": "bob@example.com", "role": "reviewer", "active_tasks": 1, "avg_review_time_min": 12.1, "accuracy": 0.91},
    {"id": "reviewer-3", "name": "Carol Wu", "email": "carol@example.com", "role": "senior_reviewer", "active_tasks": 0, "avg_review_time_min": 7.2, "accuracy": 0.98},
    {"id": "reviewer-4", "name": "Dan Okafor", "email": "dan@example.com", "role": "reviewer", "active_tasks": 0, "avg_review_time_min": 14.5, "accuracy": 0.89},
]

_MOCK_SHIFTS: list[dict[str, Any]] = [
    {"id": "shift-1", "name": "Morning US-East", "reviewer_ids": ["reviewer-1", "reviewer-2"], "start_time": "08:00", "end_time": "16:00", "timezone": "America/New_York"},
    {"id": "shift-2", "name": "Evening APAC", "reviewer_ids": ["reviewer-3"], "start_time": "20:00", "end_time": "04:00", "timezone": "Asia/Tokyo"},
]


# ---------------------------------------------------------------------------
# GET /api/reviewops/stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """Dashboard-level review operations statistics."""
    return {
        "pending": 14,
        "in_review": 3,
        "completed_today": 22,
        "overdue": 2,
        "pending_delta": 4,
        "overdue_delta": 1,
    }


# ---------------------------------------------------------------------------
# GET /api/reviewops/tasks/{task_id}/data
# ---------------------------------------------------------------------------

@router.get("/tasks/{task_id}/data")
async def get_task_data(task_id: str) -> dict[str, Any]:
    """Return mock annotation & media data for a specific task."""
    return {
        "task_id": task_id,
        "media": {
            "type": "image",
            "url": f"https://storage.example.com/media/{task_id}.jpg",
            "width": 1920,
            "height": 1080,
        },
        "annotations": [
            {"id": "ann-1", "type": "bounding_box", "label": "car", "coords": [120, 340, 450, 600], "confidence": 0.93},
            {"id": "ann-2", "type": "bounding_box", "label": "pedestrian", "coords": [800, 200, 920, 550], "confidence": 0.87},
            {"id": "ann-3", "type": "polygon", "label": "road", "points": [[0, 800], [1920, 800], [1920, 1080], [0, 1080]], "confidence": 0.99},
        ],
        "metadata": {
            "dataset": "urban-driving-v3",
            "frame_index": 1042,
            "annotator": "auto-model-v2",
            "created_at": "2026-03-20T14:22:00Z",
        },
    }


# ---------------------------------------------------------------------------
# PATCH /api/reviewops/tasks/{task_id}
# ---------------------------------------------------------------------------

@router.patch("/tasks/{task_id}")
async def patch_task(task_id: str, body: TaskPatch) -> dict[str, Any]:
    """Update status, decision, or note on a review task."""
    # Check dynamic store first
    if task_id in _tasks:
        if body.status is not None:
            _tasks[task_id]["status"] = body.status
        if body.decision is not None:
            _tasks[task_id]["decision"] = body.decision
        if body.note is not None:
            _tasks[task_id]["note"] = body.note
        return _tasks[task_id]

    # Fall back to mock tasks
    for task in _MOCK_TASKS:
        if task["id"] == task_id:
            updated = dict(task)
            if body.status is not None:
                updated["status"] = body.status
            if body.decision is not None:
                updated["decision"] = body.decision
            if body.note is not None:
                updated["note"] = body.note
            return updated

    raise HTTPException(status_code=404, detail="Task not found")


# ---------------------------------------------------------------------------
# GET /api/reviewops/reviewers
# ---------------------------------------------------------------------------

@router.get("/reviewers")
async def list_reviewers() -> list[dict[str, Any]]:
    """Return the list of available reviewers."""
    return _MOCK_REVIEWERS


# ---------------------------------------------------------------------------
# POST /api/reviewops/auto-assign
# ---------------------------------------------------------------------------

@router.post("/auto-assign")
async def auto_assign() -> dict[str, Any]:
    """Trigger automatic assignment of pending tasks to reviewers."""
    return {"assignments_made": 12, "reviewers_used": 3}


# ---------------------------------------------------------------------------
# GET /api/reviewops/leaderboard
# ---------------------------------------------------------------------------

@router.get("/leaderboard")
async def get_leaderboard(range: str = Query("week", pattern="^(day|week|month|all)$")) -> list[dict[str, Any]]:
    """Ranked reviewer leaderboard."""
    return [
        {"rank": 1, "reviewer_id": "reviewer-3", "name": "Carol Wu", "reviews_completed": 87, "accuracy": 0.98, "avg_time_min": 7.2},
        {"rank": 2, "reviewer_id": "reviewer-1", "name": "Alice Chen", "reviews_completed": 74, "accuracy": 0.96, "avg_time_min": 8.4},
        {"rank": 3, "reviewer_id": "reviewer-5", "name": "Eve Johansson", "reviews_completed": 61, "accuracy": 0.94, "avg_time_min": 9.8},
        {"rank": 4, "reviewer_id": "reviewer-2", "name": "Bob Martinez", "reviews_completed": 55, "accuracy": 0.91, "avg_time_min": 12.1},
        {"rank": 5, "reviewer_id": "reviewer-6", "name": "Frank Patel", "reviews_completed": 48, "accuracy": 0.90, "avg_time_min": 11.3},
        {"rank": 6, "reviewer_id": "reviewer-4", "name": "Dan Okafor", "reviews_completed": 39, "accuracy": 0.89, "avg_time_min": 14.5},
    ]


# ---------------------------------------------------------------------------
# GET /api/reviewops/quality
# ---------------------------------------------------------------------------

@router.get("/quality")
async def get_quality(range: str = Query("week", pattern="^(day|week|month|all)$")) -> dict[str, Any]:
    """Quality metrics including confusion matrix."""
    return {
        "range": range,
        "overall_accuracy": 0.934,
        "inter_annotator_agreement": 0.88,
        "total_reviews": 341,
        "labels": ["car", "pedestrian", "cyclist", "truck", "bus"],
        "confusion_matrix": [
            [142, 3, 1, 2, 0],
            [2, 98, 0, 0, 1],
            [1, 0, 45, 0, 0],
            [3, 0, 0, 31, 2],
            [0, 1, 0, 1, 9],
        ],
        "per_label_accuracy": {
            "car": 0.96,
            "pedestrian": 0.97,
            "cyclist": 0.98,
            "truck": 0.86,
            "bus": 0.75,
        },
    }


# ---------------------------------------------------------------------------
# GET /api/reviewops/shifts
# ---------------------------------------------------------------------------

@router.get("/shifts")
async def list_shifts() -> list[dict[str, Any]]:
    """Return configured reviewer shifts."""
    return _MOCK_SHIFTS


# ---------------------------------------------------------------------------
# POST /api/reviewops/shifts
# ---------------------------------------------------------------------------

@router.post("/shifts")
async def create_shift(body: ShiftCreate) -> dict[str, Any]:
    """Create a new reviewer shift."""
    new_shift = {
        "id": f"shift-{uuid.uuid4().hex[:6]}",
        "name": body.name,
        "reviewer_ids": body.reviewer_ids,
        "start_time": body.start_time,
        "end_time": body.end_time,
        "timezone": body.timezone,
    }
    _MOCK_SHIFTS.append(new_shift)
    return new_shift
