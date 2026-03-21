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
# Shift Schemas
# ---------------------------------------------------------------------------

class ShiftCreate(BaseModel):
    reviewer_id: str
    zone: str = "Zone A"
    date: str = ""
    time_slot: str = "Morning"
    start_time: str = ""
    end_time: str = ""


# ---------------------------------------------------------------------------
# In-memory shift store + seed data
# ---------------------------------------------------------------------------

_shifts: dict[str, dict[str, str | int | float | bool]] = {}


def _seed_shifts() -> None:
    """Populate mock shifts for the UI to render."""
    if _shifts:
        return
    seed = [
        {
            "shift_id": "shift-active-001",
            "reviewer_id": "r-001",
            "reviewer_name": "Alice M.",
            "zone": "Zone A",
            "date": "2026-03-21",
            "time_slot": "Morning",
            "start_time": "2026-03-21T06:00:00",
            "end_time": "2026-03-21T14:00:00",
            "active": True,
            "tasks_completed": 14,
            "accuracy": 94.2,
        },
        {
            "shift_id": "shift-hist-001",
            "reviewer_id": "r-002",
            "reviewer_name": "Brian K.",
            "zone": "Zone B",
            "date": "2026-03-20",
            "time_slot": "Morning",
            "start_time": "2026-03-20T06:00:00",
            "end_time": "2026-03-20T14:00:00",
            "active": False,
            "tasks_completed": 22,
            "accuracy": 96.1,
        },
        {
            "shift_id": "shift-hist-002",
            "reviewer_id": "r-001",
            "reviewer_name": "Alice M.",
            "zone": "Zone A",
            "date": "2026-03-20",
            "time_slot": "Afternoon",
            "start_time": "2026-03-20T14:00:00",
            "end_time": "2026-03-20T22:00:00",
            "active": False,
            "tasks_completed": 18,
            "accuracy": 93.4,
        },
        {
            "shift_id": "shift-hist-003",
            "reviewer_id": "r-003",
            "reviewer_name": "Carla S.",
            "zone": "Zone C",
            "date": "2026-03-19",
            "time_slot": "Morning",
            "start_time": "2026-03-19T06:00:00",
            "end_time": "2026-03-19T14:00:00",
            "active": False,
            "tasks_completed": 25,
            "accuracy": 97.8,
        },
        {
            "shift_id": "shift-hist-004",
            "reviewer_id": "r-004",
            "reviewer_name": "David L.",
            "zone": "Zone A",
            "date": "2026-03-19",
            "time_slot": "Night",
            "start_time": "2026-03-19T22:00:00",
            "end_time": "2026-03-20T06:00:00",
            "active": False,
            "tasks_completed": 12,
            "accuracy": 91.0,
        },
    ]
    for s in seed:
        _shifts[str(s["shift_id"])] = s


# ---------------------------------------------------------------------------
# Shift Endpoints
# ---------------------------------------------------------------------------

@router.get("/shifts")
async def list_shifts(
    workspace_id: str = Query(default=""),
) -> list[dict[str, str | int | float | bool]]:
    """Return all shifts (active first, then by date desc)."""
    _seed_shifts()
    shifts = list(_shifts.values())
    shifts.sort(key=lambda s: (not s.get("active", False), str(s.get("date", ""))))
    return shifts


@router.post("/shifts")
async def create_shift(
    body: ShiftCreate,
    workspace_id: str = Query(default=""),
) -> dict[str, str | int | float | bool]:
    """Create a new shift."""
    _seed_shifts()
    sid = f"shift-{uuid.uuid4().hex[:8]}"
    reviewer_names: dict[str, str] = {
        "r-001": "Alice M.",
        "r-002": "Brian K.",
        "r-003": "Carla S.",
        "r-004": "David L.",
        "r-005": "Eva R.",
    }
    shift: dict[str, str | int | float | bool] = {
        "shift_id": sid,
        "reviewer_id": body.reviewer_id,
        "reviewer_name": reviewer_names.get(body.reviewer_id, body.reviewer_id),
        "zone": body.zone,
        "date": body.date,
        "time_slot": body.time_slot,
        "start_time": body.start_time,
        "end_time": body.end_time,
        "active": False,
        "tasks_completed": 0,
        "accuracy": 0.0,
    }
    _shifts[sid] = shift
    return shift
