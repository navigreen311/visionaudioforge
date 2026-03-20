"""DoubleReviewService — consensus checking, disagreement resolution, and agreement metrics."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import (
    Review,
    ReviewDecision,
    ReviewTask,
    ReviewTaskStatus,
    ReviewType,
)

logger = logging.getLogger(__name__)


class DoubleReviewService:
    """Handles double-review workflows: consensus checking and disagreement resolution."""

    # ------------------------------------------------------------------
    # Consensus check
    # ------------------------------------------------------------------

    @staticmethod
    async def check_review_complete(
        db: AsyncSession,
        task_id: UUID,
    ) -> dict[str, Any]:
        """Check whether a task has received enough reviews and whether they agree."""
        result = await db.execute(
            select(ReviewTask)
            .options(selectinload(ReviewTask.reviews))
            .where(ReviewTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Review task {task_id} not found")

        reviews_received = len(task.reviews)
        reviews_required = task.required_reviews
        complete = reviews_received >= reviews_required

        # Determine consensus
        consensus = False
        disagreement: Optional[list[dict[str, Any]]] = None

        if reviews_received >= 2:
            decisions = [r.decision.value for r in task.reviews]
            if len(set(decisions)) == 1:
                consensus = True
            else:
                disagreement = [
                    {
                        "reviewer_id": str(r.reviewer_id),
                        "decision": r.decision.value,
                        "score": r.score,
                    }
                    for r in task.reviews
                ]
        elif reviews_received == 1 and reviews_required == 1:
            consensus = True

        return {
            "complete": complete,
            "reviews_received": reviews_received,
            "reviews_required": reviews_required,
            "consensus": consensus,
            "disagreement": disagreement,
        }

    # ------------------------------------------------------------------
    # Disagreement resolution
    # ------------------------------------------------------------------

    @staticmethod
    async def resolve_disagreement(
        db: AsyncSession,
        task_id: UUID,
        senior_reviewer_id: UUID,
        final_decision: str,
    ) -> dict[str, Any]:
        """Resolve a disagreement by having a senior reviewer make the final call."""
        result = await db.execute(
            select(ReviewTask)
            .options(selectinload(ReviewTask.reviews))
            .where(ReviewTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Review task {task_id} not found")

        # Add the senior review as the tiebreaker
        from uuid import uuid4

        review_id = uuid4()
        review = Review(
            id=review_id,
            task_id=task_id,
            reviewer_id=senior_reviewer_id,
            decision=ReviewDecision(final_decision),
            notes="Senior review — disagreement resolution",
        )
        db.add(review)
        task.status = ReviewTaskStatus.completed
        await db.flush()

        logger.info(
            "Disagreement on task %s resolved by %s: %s",
            task_id, senior_reviewer_id, final_decision,
        )
        return {
            "task_id": str(task_id),
            "status": "completed",
            "final_decision": final_decision,
            "resolved_by": str(senior_reviewer_id),
        }

    # ------------------------------------------------------------------
    # Inter-reviewer agreement
    # ------------------------------------------------------------------

    @staticmethod
    async def inter_reviewer_agreement(
        db: AsyncSession,
        workspace_id: UUID,
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Compute inter-reviewer agreement rate for double-reviewed tasks."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Get tasks with required_reviews >= 2 that are completed
        result = await db.execute(
            select(ReviewTask)
            .options(selectinload(ReviewTask.reviews))
            .where(
                and_(
                    ReviewTask.workspace_id == workspace_id,
                    ReviewTask.required_reviews >= 2,
                    ReviewTask.status == ReviewTaskStatus.completed,
                    ReviewTask.created_at >= cutoff,
                )
            )
        )
        tasks = list(result.scalars().all())

        total = len(tasks)
        agreements = 0
        disagreements = 0
        by_type: dict[str, dict[str, int]] = defaultdict(lambda: {"agreed": 0, "disagreed": 0})

        for task in tasks:
            if len(task.reviews) >= 2:
                decisions = [r.decision.value for r in task.reviews[:2]]  # first two reviews
                rtype = task.review_type.value
                if decisions[0] == decisions[1]:
                    agreements += 1
                    by_type[rtype]["agreed"] += 1
                else:
                    disagreements += 1
                    by_type[rtype]["disagreed"] += 1

        agreement_rate = (agreements / total * 100) if total > 0 else 0.0

        return {
            "agreement_rate": round(agreement_rate, 2),
            "total_double_reviewed": total,
            "disagreements": disagreements,
            "by_review_type": dict(by_type),
        }
