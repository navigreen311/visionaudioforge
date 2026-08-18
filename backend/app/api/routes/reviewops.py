"""ReviewOps routes — task management, assignments, review submissions.

Tasks are rows in ``review_tasks``. They used to live in a module-level dict
alongside hardcoded fixtures that were blended into the responses, so a fresh
install reported eight tasks named after datasets nobody had uploaded, a
leaderboard of six reviewers who did not exist, and a confusion matrix that was
written by hand. Statistics are now counted from the table, and the figures
with no source report themselves as unavailable rather than inventing a number.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.review import (
    Review,
    ReviewShift,
    ReviewTask,
    ReviewTaskStatus,
    ReviewType,
)

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
    workspace_id: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

#: Verdict -> resulting task status.
_VERDICT_STATUS = {
    "approved": ReviewTaskStatus.completed,
    "rejected": ReviewTaskStatus.escalated,
    "needs_changes": ReviewTaskStatus.in_review,
}

#: Default type for tasks created through this queue, which does not ask for one.
_DEFAULT_REVIEW_TYPE = ReviewType.annotation_qa


def _require_workspace(workspace_id: str | None) -> uuid.UUID:
    if not workspace_id:
        raise HTTPException(
            status_code=422,
            detail="workspace_id is required — review tasks are workspace-scoped",
        )
    try:
        return uuid.UUID(str(workspace_id))
    except ValueError:
        raise HTTPException(status_code=422, detail="workspace_id must be a UUID")


def _task_uuid(task_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")


def _serialise(task: ReviewTask) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "title": task.title,
        "name": task.title,
        "description": task.description,
        "asset_ids": task.asset_ids or [],
        "status": task.status.value if task.status else None,
        "priority": task.priority.value if task.priority else None,
        "type": task.review_type.value if task.review_type else None,
        "reviewer_id": task.assigned_to_label,
        "assignee": task.assigned_to_label,
        "sla_deadline": task.sla_deadline.isoformat() if task.sla_deadline else None,
        "created_at": task.created_at.timestamp() if task.created_at else None,
        "workspace_id": str(task.workspace_id) if task.workspace_id else None,
    }


async def _load(db: AsyncSession, task_id: str) -> ReviewTask:
    task = (
        await db.execute(select(ReviewTask).where(ReviewTask.id == _task_uuid(task_id)))
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _scoped(stmt, workspace_id: str | None):
    if workspace_id:
        return stmt.where(ReviewTask.workspace_id == uuid.UUID(str(workspace_id)))
    return stmt


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@router.post("/tasks", status_code=201)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Create a review task."""
    task = ReviewTask(
        workspace_id=_require_workspace(body.workspace_id),
        title=body.title,
        description=body.description,
        asset_ids=body.asset_ids,
        review_type=_DEFAULT_REVIEW_TYPE,
        status=ReviewTaskStatus.pending,
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _serialise(task)


@router.get("/tasks")
async def list_tasks(
    status: str | None = None,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List review tasks.

    Returns only real tasks. This used to concatenate eight hardcoded
    fixtures, so an empty queue looked like a busy one.
    """
    stmt = _scoped(select(ReviewTask), workspace_id)
    if status:
        stmt = stmt.where(ReviewTask.status == status)
    rows = (await db.execute(stmt.order_by(ReviewTask.created_at))).scalars().all()
    return [_serialise(t) for t in rows]


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    return _serialise(await _load(db, task_id))


@router.post("/tasks/{task_id}/assign")
async def assign_task(
    task_id: str,
    body: TaskAssign,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    task = await _load(db, task_id)
    task.assigned_to_label = body.reviewer_id
    # Link the user row too when the reviewer id is a real user.
    try:
        task.assigned_to = uuid.UUID(body.reviewer_id)
    except ValueError:
        task.assigned_to = None
    task.assigned_at = datetime.now(timezone.utc)
    task.status = ReviewTaskStatus.assigned
    await db.commit()
    await db.refresh(task)
    return _serialise(task)


@router.post("/tasks/{task_id}/review")
async def submit_review(
    task_id: str,
    body: ReviewSubmit,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Record a verdict against a task."""
    task = await _load(db, task_id)
    task.status = _VERDICT_STATUS[body.verdict]
    await db.commit()
    await db.refresh(task)

    payload = _serialise(task)
    payload["review"] = {
        "verdict": body.verdict,
        "comments": body.comments,
        "annotations": body.annotations,
        "submitted_at": datetime.now(timezone.utc).timestamp(),
    }
    return payload


@router.get("/tasks/{task_id}/status")
async def check_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    task = await _load(db, task_id)
    return {
        "task_id": task_id,
        "status": task.status.value if task.status else None,
        "completed": task.status == ReviewTaskStatus.completed,
    }


@router.patch("/tasks/{task_id}")
async def patch_task(
    task_id: str,
    body: TaskPatch,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Update status or attach a note to a review task."""
    task = await _load(db, task_id)

    if body.status is not None:
        try:
            task.status = ReviewTaskStatus(body.status)
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"Unknown status '{body.status}'"
            )
    if body.note is not None:
        task.description = body.note

    await db.commit()
    await db.refresh(task)

    payload = _serialise(task)
    if body.decision is not None:
        payload["decision"] = body.decision
    return payload


@router.get("/tasks/{task_id}/data")
async def get_task_data(
    task_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Media and annotations attached to a task.

    There is no annotation store wired to review tasks, so this reports that
    rather than returning the three hand-written bounding boxes it used to
    produce for every task id.
    """
    task = await _load(db, task_id)
    return {
        "task_id": task_id,
        "asset_ids": task.asset_ids or [],
        "media": None,
        "annotations": [],
        "supported": False,
        "detail": "Task annotation data is not wired to a store yet.",
    }


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Dashboard-level statistics, counted from the task table."""
    counts = {
        (status.value if status else "unknown"): total
        for status, total in (
            await db.execute(
                _scoped(
                    select(ReviewTask.status, func.count()).group_by(ReviewTask.status),
                    workspace_id,
                )
            )
        ).all()
    }

    now = datetime.now(timezone.utc)
    completed_today = (
        await db.execute(
            _scoped(
                select(func.count())
                .select_from(ReviewTask)
                .where(
                    ReviewTask.status == ReviewTaskStatus.completed,
                    ReviewTask.updated_at >= now - timedelta(days=1),
                ),
                workspace_id,
            )
        )
    ).scalar() or 0

    overdue = (
        await db.execute(
            _scoped(
                select(func.count())
                .select_from(ReviewTask)
                .where(
                    ReviewTask.sla_deadline < now,
                    ReviewTask.status != ReviewTaskStatus.completed,
                ),
                workspace_id,
            )
        )
    ).scalar() or 0

    return {
        "pending": counts.get("pending", 0),
        "in_review": counts.get("in_review", 0),
        "completed_today": completed_today,
        "overdue": overdue,
        # Deltas need a stored history of previous periods, which does not
        # exist. Reporting 0 would read as "no change" rather than "unknown".
        "pending_delta": None,
        "overdue_delta": None,
    }


# ---------------------------------------------------------------------------
# Reviewers
# ---------------------------------------------------------------------------

@router.get("/reviewers")
async def list_reviewers(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict[str, Any]]:
    """Reviewers, derived from who actually holds tasks.

    This used to return four invented people with names, emails and accuracy
    scores. Accuracy and average review time are null because nothing measures
    them.
    """
    rows = (
        await db.execute(
            _scoped(
                select(
                    ReviewTask.assigned_to_label,
                    func.count().label("active_tasks"),
                )
                .where(ReviewTask.assigned_to_label.isnot(None))
                .group_by(ReviewTask.assigned_to_label),
                workspace_id,
            )
        )
    ).all()

    return [
        {
            "id": label,
            "name": label,
            "active_tasks": active,
            "avg_review_time_min": None,
            "accuracy": None,
        }
        for label, active in rows
    ]


@router.post("/auto-assign")
async def auto_assign(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Assign pending tasks round-robin across known reviewers.

    Previously this reported "12 assignments made" without touching anything.
    """
    reviewers = [
        label
        for (label,) in (
            await db.execute(
                _scoped(
                    select(ReviewTask.assigned_to_label)
                    .where(ReviewTask.assigned_to_label.isnot(None))
                    .distinct(),
                    workspace_id,
                )
            )
        ).all()
    ]

    if not reviewers:
        return {
            "assignments_made": 0,
            "reviewers_used": 0,
            "detail": "No reviewers are known — assign one task manually first.",
        }

    pending = (
        await db.execute(
            _scoped(
                select(ReviewTask).where(ReviewTask.status == ReviewTaskStatus.pending),
                workspace_id,
            )
        )
    ).scalars().all()

    now = datetime.now(timezone.utc)
    for index, task in enumerate(pending):
        task.assigned_to_label = reviewers[index % len(reviewers)]
        task.assigned_at = now
        task.status = ReviewTaskStatus.assigned
    await db.commit()

    return {
        "assignments_made": len(pending),
        "reviewers_used": min(len(reviewers), len(pending)),
    }


@router.get("/leaderboard")
async def get_leaderboard(
    range: str = Query("week", pattern="^(day|week|month|all)$"),
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict[str, Any]]:
    """Reviewer leaderboard by completed tasks.

    Ranked on real completions. Accuracy and average time are null: no
    per-review timing or ground truth is recorded, and the six named reviewers
    this used to return did not exist.
    """
    rows = (
        await db.execute(
            _scoped(
                select(
                    ReviewTask.assigned_to_label,
                    func.count().label("reviews_completed"),
                )
                .where(
                    ReviewTask.assigned_to_label.isnot(None),
                    ReviewTask.status == ReviewTaskStatus.completed,
                )
                .group_by(ReviewTask.assigned_to_label)
                .order_by(func.count().desc()),
                workspace_id,
            )
        )
    ).all()

    return [
        {
            "rank": index + 1,
            "reviewer_id": label,
            "name": label,
            "reviews_completed": completed,
            "accuracy": None,
            "avg_time_min": None,
        }
        for index, (label, completed) in enumerate(rows)
    ]


@router.get("/quality")
async def get_quality(
    range: str = Query("week", pattern="^(day|week|month|all)$"),
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Quality metrics.

    Only the review count is measurable. Accuracy, inter-annotator agreement
    and the confusion matrix need ground-truth labels that are not recorded —
    the matrix this used to return was written by hand.
    """
    total_reviews = (
        await db.execute(select(func.count()).select_from(Review))
    ).scalar() or 0

    return {
        "range": range,
        "total_reviews": total_reviews,
        "overall_accuracy": None,
        "inter_annotator_agreement": None,
        "labels": [],
        "confusion_matrix": [],
        "per_label_accuracy": {},
        "supported": False,
        "detail": "Quality scoring requires ground-truth labels that are not recorded.",
    }


# ---------------------------------------------------------------------------
# Shifts
# ---------------------------------------------------------------------------

@router.get("/shifts")
async def list_shifts(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict[str, Any]]:
    """Return configured reviewer shifts."""
    stmt = select(ReviewShift)
    if workspace_id:
        stmt = stmt.where(ReviewShift.workspace_id == uuid.UUID(str(workspace_id)))
    rows = (await db.execute(stmt.order_by(ReviewShift.start_time))).scalars().all()

    return [
        {
            "id": str(s.id),
            "name": s.notes,
            "reviewer_ids": [str(s.reviewer_id)],
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "review_types": s.review_types or [],
            "active": s.active,
        }
        for s in rows
    ]


@router.post("/shifts", status_code=201)
async def create_shift(
    body: ShiftCreate,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Create a reviewer shift.

    ``review_shifts`` ties a shift to exactly one reviewer, so a request naming
    several is rejected rather than silently keeping only the first.
    """
    workspace_id = _require_workspace(body.workspace_id)

    if len(body.reviewer_ids) != 1:
        raise HTTPException(
            status_code=422,
            detail="Exactly one reviewer_id is required per shift",
        )
    try:
        reviewer_id = uuid.UUID(body.reviewer_ids[0])
    except ValueError:
        raise HTTPException(status_code=422, detail="reviewer_id must be a UUID")

    def _parse(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="start_time and end_time must be ISO-8601 timestamps",
            )

    shift = ReviewShift(
        workspace_id=workspace_id,
        reviewer_id=reviewer_id,
        start_time=_parse(body.start_time),
        end_time=_parse(body.end_time),
        notes=body.name,
    )
    db.add(shift)
    await db.commit()
    await db.refresh(shift)

    return {
        "id": str(shift.id),
        "name": body.name,
        "reviewer_ids": [str(shift.reviewer_id)],
        "start_time": shift.start_time.isoformat(),
        "end_time": shift.end_time.isoformat(),
        "timezone": body.timezone,
    }
