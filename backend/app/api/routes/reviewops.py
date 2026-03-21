"""ReviewOps routes — task management, assignments, review submissions."""

from __future__ import annotations

import random
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


class TrendPoint(BaseModel):
    day: int
    value: float


class ReviewerEntry(BaseModel):
    id: str
    name: str
    avatar_url: str
    tasks_completed: int
    max_tasks: int
    accuracy: float
    avg_review_time_sec: int
    streak_days: int
    trend: list[TrendPoint]


class LeaderboardResponse(BaseModel):
    range: str
    entries: list[ReviewerEntry]
    my_stats: ReviewerEntry | None = None


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
# Leaderboard — mock data
# ---------------------------------------------------------------------------

_MOCK_REVIEWERS = [
    {"id": "r1", "name": "Alice Chen",     "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=alice"},
    {"id": "r2", "name": "Bob Martinez",   "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=bob"},
    {"id": "r3", "name": "Carol Nguyen",   "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=carol"},
    {"id": "r4", "name": "David Kim",      "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=david"},
    {"id": "r5", "name": "Eva Johansson",  "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=eva"},
    {"id": "r6", "name": "Frank Okafor",   "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=frank"},
]

_RANGE_MULTIPLIER: dict[str, float] = {"today": 0.15, "week": 1.0, "month": 4.0}


def _build_mock_entries(time_range: str) -> list[ReviewerEntry]:
    """Generate deterministic-but-varied mock leaderboard entries."""
    rng = random.Random(42)
    mult = _RANGE_MULTIPLIER.get(time_range, 1.0)
    entries: list[ReviewerEntry] = []

    base_tasks = [47, 42, 38, 31, 25, 18]
    base_accuracy = [97.3, 94.8, 96.1, 88.5, 91.2, 85.0]
    base_time = [45, 62, 53, 78, 95, 120]
    base_streak = [12, 5, 8, 3, 0, 7]

    for i, reviewer in enumerate(_MOCK_REVIEWERS):
        tasks = max(1, int(base_tasks[i] * mult))
        max_tasks = max(tasks, int(base_tasks[0] * mult))
        trend = [
            TrendPoint(day=d, value=round(rng.uniform(0.6, 1.0) * base_tasks[i] * mult / 7, 1))
            for d in range(7)
        ]
        entries.append(
            ReviewerEntry(
                id=reviewer["id"],
                name=reviewer["name"],
                avatar_url=reviewer["avatar_url"],
                tasks_completed=tasks,
                max_tasks=max_tasks,
                accuracy=base_accuracy[i],
                avg_review_time_sec=base_time[i],
                streak_days=base_streak[i],
                trend=trend,
            )
        )

    entries.sort(key=lambda e: e.tasks_completed, reverse=True)
    return entries


@router.get("/leaderboard")
async def get_leaderboard(
    time_range: Literal["today", "week", "month"] = Query("week", alias="range"),
) -> LeaderboardResponse:
    """Return reviewer leaderboard with mock data."""
    entries = _build_mock_entries(time_range)

    # Treat the 4th reviewer (David Kim) as "me" for the My Stats panel
    my_stats = next((e for e in entries if e.id == "r4"), None)

    return LeaderboardResponse(range=time_range, entries=entries, my_stats=my_stats)
