"""ReviewOps routes — task management, assignments, review submissions, quality."""

from __future__ import annotations

import math
import random
import time
import uuid
from datetime import date, timedelta
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


# ---------------------------------------------------------------------------
# Quality schemas
# ---------------------------------------------------------------------------


class QualitySummary(BaseModel):
    inter_rater_agreement: float
    rejection_rate: float
    escalation_rate: float
    avg_quality_score: float


class AccuracyPoint(BaseModel):
    date: str
    accuracy: float


class DisagreementCase(BaseModel):
    task_id: str
    task_type: str
    reviewer_a: str
    reviewer_b: str
    decision_a: str
    decision_b: str
    resolved: bool


class ConfusionMatrixData(BaseModel):
    labels: list[str]
    values: list[list[int]]


class QualityResponse(BaseModel):
    summary: QualitySummary
    accuracy_trend: list[AccuracyPoint]
    disagreements: list[DisagreementCase]
    confusion_matrix: ConfusionMatrixData


class TieBreakRequest(BaseModel):
    task_id: str
    verdict: Literal["approve", "reject"]


# ---------------------------------------------------------------------------
# Quality mock data generator
# ---------------------------------------------------------------------------

_MOCK_REVIEWERS = ["alice", "bob", "carol", "dave"]
_MOCK_TASK_TYPES = ["bbox", "classification", "segmentation", "caption"]
_MOCK_LABELS = ["person", "vehicle", "animal", "object"]


def _generate_quality_mock(range_param: str) -> dict[str, Any]:
    """Generate deterministic-ish mock quality metrics."""
    random.seed(42)

    days = 7 if range_param == "week" else 30
    today = date(2026, 3, 21)

    # Summary
    summary = QualitySummary(
        inter_rater_agreement=87.3,
        rejection_rate=12.5,
        escalation_rate=4.2,
        avg_quality_score=91.8,
    )

    # Accuracy trend (14 data points)
    trend_days = min(days, 14)
    accuracy_trend: list[AccuracyPoint] = []
    for i in range(trend_days):
        d = today - timedelta(days=trend_days - 1 - i)
        acc = 0.88 + 0.08 * math.sin(i * 0.5) + random.uniform(-0.02, 0.02)
        accuracy_trend.append(
            AccuracyPoint(date=d.isoformat(), accuracy=round(min(max(acc, 0.75), 0.99), 4))
        )

    # Disagreements
    disagreements: list[DisagreementCase] = []
    for i in range(5):
        a_idx = i % len(_MOCK_REVIEWERS)
        b_idx = (i + 1) % len(_MOCK_REVIEWERS)
        disagreements.append(
            DisagreementCase(
                task_id=str(uuid.UUID(int=1000 + i)),
                task_type=_MOCK_TASK_TYPES[i % len(_MOCK_TASK_TYPES)],
                reviewer_a=_MOCK_REVIEWERS[a_idx],
                reviewer_b=_MOCK_REVIEWERS[b_idx],
                decision_a="approved",
                decision_b="rejected",
                resolved=i >= 3,
            )
        )

    # Confusion matrix (4x4)
    confusion_matrix = ConfusionMatrixData(
        labels=_MOCK_LABELS,
        values=[
            [42, 3, 1, 2],
            [2, 38, 0, 4],
            [1, 0, 35, 1],
            [3, 2, 1, 40],
        ],
    )

    return QualityResponse(
        summary=summary,
        accuracy_trend=accuracy_trend,
        disagreements=disagreements,
        confusion_matrix=confusion_matrix,
    ).model_dump()


# ---------------------------------------------------------------------------
# Quality endpoints
# ---------------------------------------------------------------------------


@router.get("/quality")
async def get_quality_metrics(
    range: str = Query("week", pattern="^(week|month)$"),  # noqa: A002
) -> dict[str, Any]:
    """Return quality metrics for the ReviewOps Quality tab.

    Stub: returns mock data. Replace with real aggregation queries once
    the review data store is wired up.
    """
    return _generate_quality_mock(range)


@router.post("/quality/tiebreak")
async def submit_tiebreak(body: TieBreakRequest) -> dict[str, str]:
    """Record a tie-break decision for a disagreement case.

    Stub: accepts any task_id and returns success.
    """
    return {
        "task_id": body.task_id,
        "verdict": body.verdict,
        "status": "resolved",
    }
