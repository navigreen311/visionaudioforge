"""ShiftManager — reviewer shift scheduling, handoffs, and shift reporting."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import (
    Review,
    ReviewShift,
    ReviewTask,
    ReviewTaskStatus,
)

logger = logging.getLogger(__name__)


class ShiftManager:
    """Manages reviewer shift schedules, handoffs, and reporting."""

    # ------------------------------------------------------------------
    # Shift creation
    # ------------------------------------------------------------------

    @staticmethod
    async def create_review_shift(
        db: AsyncSession,
        workspace_id: UUID,
        reviewer_id: UUID,
        start: datetime,
        end: datetime,
        review_types: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Create a new review shift."""
        shift_id = uuid4()
        shift = ReviewShift(
            id=shift_id,
            workspace_id=workspace_id,
            reviewer_id=reviewer_id,
            start_time=start,
            end_time=end,
            review_types=review_types,
            active=True,
        )
        db.add(shift)
        await db.flush()

        logger.info("Created shift %s for reviewer %s", shift_id, reviewer_id)
        return {
            "shift_id": str(shift_id),
            "workspace_id": str(workspace_id),
            "reviewer_id": str(reviewer_id),
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "review_types": review_types,
            "active": True,
        }

    # ------------------------------------------------------------------
    # Active reviewers
    # ------------------------------------------------------------------

    @staticmethod
    async def get_active_reviewers(
        db: AsyncSession,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get reviewers currently on shift."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(ReviewShift).where(
                and_(
                    ReviewShift.workspace_id == workspace_id,
                    ReviewShift.start_time <= now,
                    ReviewShift.end_time >= now,
                    ReviewShift.active == True,  # noqa: E712
                )
            )
        )
        shifts = result.scalars().all()
        return [
            {
                "reviewer_id": str(s.reviewer_id),
                "shift_id": str(s.id),
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "review_types": s.review_types,
            }
            for s in shifts
        ]

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    @staticmethod
    async def get_shift_schedule(
        db: AsyncSession,
        workspace_id: UUID,
        date_range: tuple[datetime, datetime],
    ) -> list[dict[str, Any]]:
        """Get shift schedule for a date range."""
        start, end = date_range
        result = await db.execute(
            select(ReviewShift)
            .where(
                and_(
                    ReviewShift.workspace_id == workspace_id,
                    ReviewShift.start_time >= start,
                    ReviewShift.end_time <= end,
                )
            )
            .order_by(ReviewShift.start_time)
        )
        shifts = result.scalars().all()
        return [
            {
                "shift_id": str(s.id),
                "reviewer_id": str(s.reviewer_id),
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "review_types": s.review_types,
                "active": s.active,
            }
            for s in shifts
        ]

    # ------------------------------------------------------------------
    # Handoff
    # ------------------------------------------------------------------

    @staticmethod
    async def handoff(
        db: AsyncSession,
        from_shift_id: UUID,
        to_shift_id: UUID,
        notes: str,
    ) -> dict[str, Any]:
        """Transfer incomplete tasks from ending shift to new shift's reviewer."""
        # Get from shift
        from_result = await db.execute(
            select(ReviewShift).where(ReviewShift.id == from_shift_id)
        )
        from_shift = from_result.scalar_one_or_none()
        if not from_shift:
            raise ValueError(f"Shift {from_shift_id} not found")

        # Get to shift
        to_result = await db.execute(
            select(ReviewShift).where(ReviewShift.id == to_shift_id)
        )
        to_shift = to_result.scalar_one_or_none()
        if not to_shift:
            raise ValueError(f"Shift {to_shift_id} not found")

        # Find pending/assigned tasks for the outgoing reviewer
        task_result = await db.execute(
            select(ReviewTask).where(
                and_(
                    ReviewTask.assigned_to == from_shift.reviewer_id,
                    ReviewTask.workspace_id == from_shift.workspace_id,
                    ReviewTask.status.in_([
                        ReviewTaskStatus.assigned,
                        ReviewTaskStatus.in_review,
                    ]),
                )
            )
        )
        tasks = list(task_result.scalars().all())

        # Transfer tasks
        now = datetime.now(timezone.utc)
        for task in tasks:
            task.assigned_to = to_shift.reviewer_id
            task.assigned_at = now

        # Deactivate old shift
        from_shift.active = False
        from_shift.notes = notes

        await db.flush()
        logger.info(
            "Handoff: %d tasks from shift %s to shift %s",
            len(tasks), from_shift_id, to_shift_id,
        )
        return {"pending_tasks_transferred": len(tasks)}

    # ------------------------------------------------------------------
    # Shift report
    # ------------------------------------------------------------------

    @staticmethod
    async def shift_report(
        db: AsyncSession,
        shift_id: UUID,
    ) -> dict[str, Any]:
        """Generate a report for a completed shift."""
        result = await db.execute(
            select(ReviewShift).where(ReviewShift.id == shift_id)
        )
        shift = result.scalar_one_or_none()
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")

        duration_h = (shift.end_time - shift.start_time).total_seconds() / 3600

        # Reviews completed during this shift
        review_result = await db.execute(
            select(Review).where(
                and_(
                    Review.reviewer_id == shift.reviewer_id,
                    Review.created_at >= shift.start_time,
                    Review.created_at <= shift.end_time,
                )
            )
        )
        reviews = list(review_result.scalars().all())
        tasks_completed = len(reviews)

        scores = [r.score for r in reviews if r.score is not None]
        avg_quality = sum(scores) / len(scores) if scores else 0.0

        # SLA breaches during shift
        task_ids = [r.task_id for r in reviews]
        sla_breaches = 0
        if task_ids:
            task_result = await db.execute(
                select(ReviewTask).where(ReviewTask.id.in_(task_ids))
            )
            tasks = list(task_result.scalars().all())
            for task in tasks:
                for rev in reviews:
                    if rev.task_id == task.id and rev.created_at and task.sla_deadline:
                        if rev.created_at > task.sla_deadline:
                            sla_breaches += 1
                        break

        return {
            "reviewer": str(shift.reviewer_id),
            "duration_h": round(duration_h, 2),
            "tasks_completed": tasks_completed,
            "avg_quality": round(avg_quality, 2),
            "sla_breaches": sla_breaches,
        }
