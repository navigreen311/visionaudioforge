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
