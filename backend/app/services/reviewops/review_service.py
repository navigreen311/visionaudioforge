"""ReviewService — core review task management, assignment, and SLA tracking."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import (
    Review,
    ReviewDecision,
    ReviewPriority,
    ReviewTask,
    ReviewTaskStatus,
    ReviewType,
)

logger = logging.getLogger(__name__)

# Valid review types for validation
VALID_REVIEW_TYPES = {e.value for e in ReviewType}
VALID_PRIORITIES = {e.value for e in ReviewPriority}
VALID_DECISIONS = {e.value for e in ReviewDecision}


class ReviewService:
    """Manages review task lifecycle: creation, assignment, submission, and SLA checks."""

    # ------------------------------------------------------------------
    # Task creation
    # ------------------------------------------------------------------

    @staticmethod
    async def create_review_task(
        db: AsyncSession,
        workspace_id: UUID,
        asset_id: UUID,
        review_type: str,
        priority: str = "normal",
        required_reviews: int = 1,
        sla_hours: float = 24.0,
    ) -> dict[str, Any]:
        """Create a new review task with an SLA deadline."""
        now = datetime.now(timezone.utc)
        sla_deadline = now + timedelta(hours=sla_hours)
        task_id = uuid4()

        task = ReviewTask(
            id=task_id,
            workspace_id=workspace_id,
            asset_id=asset_id,
            review_type=ReviewType(review_type),
            priority=ReviewPriority(priority),
            status=ReviewTaskStatus.pending,
            required_reviews=required_reviews,
            sla_hours=sla_hours,
            sla_deadline=sla_deadline,
        )
        db.add(task)
        await db.flush()

        logger.info("Created review task %s for asset %s (SLA: %sh)", task_id, asset_id, sla_hours)
        return {
            "task_id": str(task_id),
            "status": "pending",
            "sla_deadline": sla_deadline.isoformat(),
        }

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    @staticmethod
    async def assign_reviewer(
        db: AsyncSession,
        task_id: UUID,
        reviewer_id: UUID,
        auto: bool = False,
    ) -> dict[str, Any]:
        """Assign a reviewer to a task."""
        result = await db.execute(
            select(ReviewTask).where(ReviewTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Review task {task_id} not found")

        now = datetime.now(timezone.utc)
        task.assigned_to = reviewer_id
        task.assigned_at = now
        task.status = ReviewTaskStatus.assigned
        await db.flush()

        logger.info("Assigned reviewer %s to task %s (auto=%s)", reviewer_id, task_id, auto)
        return {
            "assigned_to": str(reviewer_id),
            "assigned_at": now.isoformat(),
        }

    @staticmethod
    async def auto_assign_tasks(
        db: AsyncSession,
        workspace_id: UUID,
    ) -> dict[str, Any]:
        """Auto-assign all pending tasks using round-robin among active reviewers.

        Assigns to the reviewer with the fewest active tasks (least loaded).
        """
        # Get pending tasks
        pending_result = await db.execute(
            select(ReviewTask)
            .where(
                and_(
                    ReviewTask.workspace_id == workspace_id,
                    ReviewTask.status == ReviewTaskStatus.pending,
                )
            )
            .order_by(ReviewTask.created_at)
        )
        pending_tasks = list(pending_result.scalars().all())

        if not pending_tasks:
            return {"assigned": 0}

        # Get reviewers and their workloads — count active tasks per reviewer
        workload_result = await db.execute(
            select(
                ReviewTask.assigned_to,
                func.count(ReviewTask.id).label("active_count"),
            )
            .where(
                and_(
                    ReviewTask.workspace_id == workspace_id,
                    ReviewTask.assigned_to.isnot(None),
                    ReviewTask.status.in_([
                        ReviewTaskStatus.assigned,
                        ReviewTaskStatus.in_review,
                    ]),
                )
            )
            .group_by(ReviewTask.assigned_to)
        )
        workload_map: dict[UUID, int] = {}
        for row in workload_result:
            workload_map[row[0]] = row[1]

        # Get distinct reviewers who have been assigned before in this workspace
        reviewer_result = await db.execute(
            select(ReviewTask.assigned_to)
            .where(
                and_(
                    ReviewTask.workspace_id == workspace_id,
                    ReviewTask.assigned_to.isnot(None),
                )
            )
            .distinct()
        )
        reviewers = [r[0] for r in reviewer_result]

        if not reviewers:
            logger.warning("No reviewers available for auto-assignment in workspace %s", workspace_id)
            return {"assigned": 0}

        now = datetime.now(timezone.utc)
        assigned_count = 0

        for task in pending_tasks:
            # Find least loaded reviewer
            least_loaded = min(reviewers, key=lambda r: workload_map.get(r, 0))
            task.assigned_to = least_loaded
            task.assigned_at = now
            task.status = ReviewTaskStatus.assigned
            workload_map[least_loaded] = workload_map.get(least_loaded, 0) + 1
            assigned_count += 1

        await db.flush()
        logger.info("Auto-assigned %d tasks in workspace %s", assigned_count, workspace_id)
        return {"assigned": assigned_count}

    # ------------------------------------------------------------------
    # Review submission
    # ------------------------------------------------------------------

    @staticmethod
    async def submit_review(
        db: AsyncSession,
        task_id: UUID,
        reviewer_id: UUID,
        decision: str,
        score: Optional[int] = None,
        notes: Optional[str] = None,
        corrections: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Submit a review for a task."""
        result = await db.execute(
            select(ReviewTask)
            .options(selectinload(ReviewTask.reviews))
            .where(ReviewTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Review task {task_id} not found")

        # Calculate review time from assignment
        review_time_s = None
        if task.assigned_at:
            review_time_s = (datetime.now(timezone.utc) - task.assigned_at).total_seconds()

        review_id = uuid4()
        review = Review(
            id=review_id,
            task_id=task_id,
            reviewer_id=reviewer_id,
            decision=ReviewDecision(decision),
            score=score,
            notes=notes,
            corrections=corrections,
            review_time_seconds=review_time_s,
        )
        db.add(review)

        # Update task status based on review count
        reviews_received = len(task.reviews) + 1
        if decision == "escalated":
            task.status = ReviewTaskStatus.escalated
        elif reviews_received >= task.required_reviews:
            task.status = ReviewTaskStatus.completed
        else:
            task.status = ReviewTaskStatus.in_review

        await db.flush()
        logger.info("Review %s submitted for task %s: %s", review_id, task_id, decision)
        return {
            "review_id": str(review_id),
            "decision": decision,
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @staticmethod
    async def get_task(db: AsyncSession, task_id: UUID) -> dict[str, Any]:
        """Get a task with all its reviews."""
        result = await db.execute(
            select(ReviewTask)
            .options(selectinload(ReviewTask.reviews))
            .where(ReviewTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Review task {task_id} not found")

        return {
            "task_id": str(task.id),
            "workspace_id": str(task.workspace_id),
            "asset_id": str(task.asset_id),
            "review_type": task.review_type.value,
            "priority": task.priority.value,
            "status": task.status.value,
            "required_reviews": task.required_reviews,
            "sla_hours": task.sla_hours,
            "sla_deadline": task.sla_deadline.isoformat(),
            "assigned_to": str(task.assigned_to) if task.assigned_to else None,
            "assigned_at": task.assigned_at.isoformat() if task.assigned_at else None,
            "reviews": [
                {
                    "review_id": str(r.id),
                    "reviewer_id": str(r.reviewer_id),
                    "decision": r.decision.value,
                    "score": r.score,
                    "notes": r.notes,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in task.reviews
            ],
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }

    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        workspace_id: UUID,
        status: Optional[str] = None,
        reviewer_id: Optional[UUID] = None,
        priority: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List tasks for a workspace, with optional filters."""
        query = (
            select(ReviewTask)
            .options(selectinload(ReviewTask.reviews))
            .where(ReviewTask.workspace_id == workspace_id)
        )

        if status:
            query = query.where(ReviewTask.status == ReviewTaskStatus(status))
        if reviewer_id:
            query = query.where(ReviewTask.assigned_to == reviewer_id)
        if priority:
            query = query.where(ReviewTask.priority == ReviewPriority(priority))

        query = query.order_by(ReviewTask.created_at.desc())
        result = await db.execute(query)
        tasks = result.scalars().all()

        return [
            {
                "task_id": str(t.id),
                "review_type": t.review_type.value,
                "priority": t.priority.value,
                "status": t.status.value,
                "sla_deadline": t.sla_deadline.isoformat(),
                "assigned_to": str(t.assigned_to) if t.assigned_to else None,
                "reviews_count": len(t.reviews),
                "required_reviews": t.required_reviews,
            }
            for t in tasks
        ]

    # ------------------------------------------------------------------
    # SLA
    # ------------------------------------------------------------------

    @staticmethod
    async def check_sla_breaches(
        db: AsyncSession,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """Return tasks that have exceeded their SLA deadline."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(ReviewTask).where(
                and_(
                    ReviewTask.workspace_id == workspace_id,
                    ReviewTask.sla_deadline < now,
                    ReviewTask.status.in_([
                        ReviewTaskStatus.pending,
                        ReviewTaskStatus.assigned,
                        ReviewTaskStatus.in_review,
                    ]),
                )
            )
        )
        breached = result.scalars().all()
        return [
            {
                "task_id": str(t.id),
                "sla_deadline": t.sla_deadline.isoformat(),
                "overdue_hours": round((now - t.sla_deadline).total_seconds() / 3600, 2),
                "status": t.status.value,
                "review_type": t.review_type.value,
            }
            for t in breached
        ]

    # ------------------------------------------------------------------
    # Workload
    # ------------------------------------------------------------------

    @staticmethod
    async def get_reviewer_workload(
        db: AsyncSession,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get workload stats for all reviewers in a workspace."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Active tasks per reviewer
        active_result = await db.execute(
            select(
                ReviewTask.assigned_to,
                func.count(ReviewTask.id).label("active_count"),
            )
            .where(
                and_(
                    ReviewTask.workspace_id == workspace_id,
                    ReviewTask.assigned_to.isnot(None),
                    ReviewTask.status.in_([
                        ReviewTaskStatus.assigned,
                        ReviewTaskStatus.in_review,
                    ]),
                )
            )
            .group_by(ReviewTask.assigned_to)
        )
        active_map: dict[str, int] = {}
        reviewer_ids: set[UUID] = set()
        for row in active_result:
            active_map[str(row[0])] = row[1]
            reviewer_ids.add(row[0])

        # Completed today per reviewer
        completed_result = await db.execute(
            select(
                Review.reviewer_id,
                func.count(Review.id).label("completed_count"),
            )
            .where(Review.created_at >= today_start)
            .group_by(Review.reviewer_id)
        )
        completed_map: dict[str, int] = {}
        for row in completed_result:
            completed_map[str(row[0])] = row[1]
            reviewer_ids.add(row[0])

        # Avg review time per reviewer
        avg_time_result = await db.execute(
            select(
                Review.reviewer_id,
                func.avg(Review.review_time_seconds).label("avg_time"),
            )
            .where(Review.review_time_seconds.isnot(None))
            .group_by(Review.reviewer_id)
        )
        avg_time_map: dict[str, float] = {}
        for row in avg_time_result:
            avg_time_map[str(row[0])] = round(float(row[1]), 2) if row[1] else 0.0
            reviewer_ids.add(row[0])

        return [
            {
                "reviewer_id": str(rid),
                "active_tasks": active_map.get(str(rid), 0),
                "completed_today": completed_map.get(str(rid), 0),
                "avg_review_time_s": avg_time_map.get(str(rid), 0.0),
            }
            for rid in reviewer_ids
        ]
