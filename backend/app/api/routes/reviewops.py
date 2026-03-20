"""ReviewOps routes — review tasks, assignments, quality scoring, and shift management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.services.reviewops.review_service import ReviewService
from app.services.reviewops.double_review import DoubleReviewService
from app.services.reviewops.quality_scoring import QualityScoring
from app.services.reviewops.shift_management import ShiftManager

router = APIRouter(prefix="/api/reviewops", tags=["reviewops"])


# ------------------------------------------------------------------
# Review Task endpoints
# ------------------------------------------------------------------


@router.post("/tasks", status_code=201)
async def create_review_task(
    body: dict,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new review task."""
    try:
        result = await ReviewService.create_review_task(
            db,
            workspace_id=workspace_id,
            asset_id=UUID(body["asset_id"]),
            review_type=body["review_type"],
            priority=body.get("priority", "normal"),
            required_reviews=body.get("required_reviews", 1),
            sla_hours=body.get("sla_hours", 24.0),
        )
        await db.commit()
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks")
async def list_tasks(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    status: Optional[str] = Query(None),
    reviewer_id: Optional[UUID] = Query(None),
    priority: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    """List review tasks with optional filters."""
    try:
        return await ReviewService.list_tasks(
            db, workspace_id, status=status, reviewer_id=reviewer_id, priority=priority,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a review task with all its reviews."""
    try:
        return await ReviewService.get_task(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tasks/{task_id}/assign")
async def assign_reviewer(
    task_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_async_session),
):
    """Assign a reviewer to a task."""
    try:
        result = await ReviewService.assign_reviewer(
            db,
            task_id=task_id,
            reviewer_id=UUID(body["reviewer_id"]),
            auto=body.get("auto", False),
        )
        await db.commit()
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/auto-assign")
async def auto_assign_tasks(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Auto-assign all pending tasks in a workspace."""
    result = await ReviewService.auto_assign_tasks(db, workspace_id)
    await db.commit()
    return result


@router.post("/tasks/{task_id}/review")
async def submit_review(
    task_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_async_session),
):
    """Submit a review for a task."""
    try:
        result = await ReviewService.submit_review(
            db,
            task_id=task_id,
            reviewer_id=UUID(body["reviewer_id"]),
            decision=body["decision"],
            score=body.get("score"),
            notes=body.get("notes"),
            corrections=body.get("corrections"),
        )
        await db.commit()
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------
# SLA
# ------------------------------------------------------------------


@router.get("/sla-breaches")
async def list_sla_breaches(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """List tasks that have exceeded their SLA deadline."""
    return await ReviewService.check_sla_breaches(db, workspace_id)


# ------------------------------------------------------------------
# Workload
# ------------------------------------------------------------------


@router.get("/workload")
async def get_workload(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get reviewer workload stats."""
    return await ReviewService.get_reviewer_workload(db, workspace_id)


# ------------------------------------------------------------------
# Double Review / Disagreement
# ------------------------------------------------------------------


@router.post("/tasks/{task_id}/resolve")
async def resolve_disagreement(
    task_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_async_session),
):
    """Resolve a disagreement via senior review."""
    try:
        result = await DoubleReviewService.resolve_disagreement(
            db,
            task_id=task_id,
            senior_reviewer_id=UUID(body["senior_reviewer_id"]),
            final_decision=body["final_decision"],
        )
        await db.commit()
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agreement")
async def get_agreement(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    period_days: int = Query(30),
    db: AsyncSession = Depends(get_async_session),
):
    """Get inter-reviewer agreement statistics."""
    return await DoubleReviewService.inter_reviewer_agreement(db, workspace_id, period_days)


# ------------------------------------------------------------------
# Quality Scoring
# ------------------------------------------------------------------


@router.get("/leaderboard")
async def get_leaderboard(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    period_days: int = Query(30),
    db: AsyncSession = Depends(get_async_session),
):
    """Get reviewer leaderboard ranked by quality grade."""
    return await QualityScoring.leaderboard(db, workspace_id, period_days)


@router.get("/quality-trends")
async def get_quality_trends(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    period: str = Query("weekly"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get quality trends over time."""
    return await QualityScoring.quality_trends(db, workspace_id, period)


# ------------------------------------------------------------------
# Shift Management
# ------------------------------------------------------------------


@router.post("/shifts", status_code=201)
async def create_shift(
    body: dict,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new review shift."""
    try:
        result = await ShiftManager.create_review_shift(
            db,
            workspace_id=workspace_id,
            reviewer_id=UUID(body["reviewer_id"]),
            start=datetime.fromisoformat(body["start"]),
            end=datetime.fromisoformat(body["end"]),
            review_types=body.get("review_types"),
        )
        await db.commit()
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/shifts")
async def list_shifts(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    """Get shift schedule for a workspace."""
    if start and end:
        date_range = (
            datetime.fromisoformat(start),
            datetime.fromisoformat(end),
        )
        return await ShiftManager.get_shift_schedule(db, workspace_id, date_range)
    return await ShiftManager.get_active_reviewers(db, workspace_id)


@router.post("/shifts/{shift_id}/handoff")
async def shift_handoff(
    shift_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_async_session),
):
    """Handoff tasks from one shift to another."""
    try:
        result = await ShiftManager.handoff(
            db,
            from_shift_id=shift_id,
            to_shift_id=UUID(body["to_shift_id"]),
            notes=body["notes"],
        )
        await db.commit()
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
