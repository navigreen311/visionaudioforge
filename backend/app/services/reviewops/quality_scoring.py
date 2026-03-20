"""QualityScoring — reviewer grades, leaderboards, asset quality, and trend analysis."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.review import (
    Review,
    ReviewTask,
    ReviewTaskStatus,
)

logger = logging.getLogger(__name__)


def _compute_grade(score: float) -> str:
    """Map a 0-100 composite score to a letter grade."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


class QualityScoring:
    """Quality metrics for reviewers and assets."""

    # ------------------------------------------------------------------
    # Reviewer scoring
    # ------------------------------------------------------------------

    @staticmethod
    async def compute_reviewer_score(
        db: AsyncSession,
        reviewer_id: UUID,
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Compute a composite quality score for a reviewer."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Get all reviews by this reviewer in the period
        result = await db.execute(
            select(Review)
            .where(
                and_(
                    Review.reviewer_id == reviewer_id,
                    Review.created_at >= cutoff,
                )
            )
        )
        reviews = list(result.scalars().all())
        total_reviews = len(reviews)

        if total_reviews == 0:
            return {
                "reviewer_id": str(reviewer_id),
                "total_reviews": 0,
                "avg_quality_score": 0.0,
                "avg_review_time_s": 0.0,
                "sla_compliance_pct": 0.0,
                "agreement_rate": 0.0,
                "overall_grade": "F",
            }

        # Average quality score (from score field, 1-5 mapped to 0-100)
        scored = [r.score for r in reviews if r.score is not None]
        avg_quality = (sum(scored) / len(scored) / 5 * 100) if scored else 50.0

        # Average review time
        times = [r.review_time_seconds for r in reviews if r.review_time_seconds is not None]
        avg_time = sum(times) / len(times) if times else 0.0

        # SLA compliance — check how many of their reviewed tasks were within SLA
        task_ids = [r.task_id for r in reviews]
        sla_compliant = 0
        if task_ids:
            task_result = await db.execute(
                select(ReviewTask).where(ReviewTask.id.in_(task_ids))
            )
            tasks = list(task_result.scalars().all())
            for task in tasks:
                for rev in reviews:
                    if rev.task_id == task.id and rev.created_at and task.sla_deadline:
                        if rev.created_at <= task.sla_deadline:
                            sla_compliant += 1
                        break
        sla_pct = (sla_compliant / total_reviews * 100) if total_reviews > 0 else 0.0

        # Agreement rate — for tasks with multiple reviews, did this reviewer agree?
        agreement_count = 0
        agreement_total = 0
        if task_ids:
            multi_result = await db.execute(
                select(ReviewTask)
                .options(selectinload(ReviewTask.reviews))
                .where(
                    and_(
                        ReviewTask.id.in_(task_ids),
                        ReviewTask.required_reviews >= 2,
                    )
                )
            )
            multi_tasks = list(multi_result.scalars().all())
            for task in multi_tasks:
                if len(task.reviews) >= 2:
                    agreement_total += 1
                    this_decision = None
                    other_decisions = []
                    for r in task.reviews:
                        if r.reviewer_id == reviewer_id:
                            this_decision = r.decision.value
                        else:
                            other_decisions.append(r.decision.value)
                    if this_decision and this_decision in other_decisions:
                        agreement_count += 1

        agreement_rate = (agreement_count / agreement_total * 100) if agreement_total > 0 else 100.0

        # Composite score (equal weighting)
        composite = (avg_quality + sla_pct + agreement_rate) / 3
        grade = _compute_grade(composite)

        return {
            "reviewer_id": str(reviewer_id),
            "total_reviews": total_reviews,
            "avg_quality_score": round(avg_quality, 2),
            "avg_review_time_s": round(avg_time, 2),
            "sla_compliance_pct": round(sla_pct, 2),
            "agreement_rate": round(agreement_rate, 2),
            "overall_grade": grade,
        }

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    @staticmethod
    async def leaderboard(
        db: AsyncSession,
        workspace_id: UUID,
        period_days: int = 30,
    ) -> list[dict[str, Any]]:
        """Return reviewers ranked by overall grade."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Get distinct reviewers for this workspace
        result = await db.execute(
            select(Review.reviewer_id)
            .join(ReviewTask, Review.task_id == ReviewTask.id)
            .where(
                and_(
                    ReviewTask.workspace_id == workspace_id,
                    Review.created_at >= cutoff,
                )
            )
            .distinct()
        )
        reviewer_ids = [row[0] for row in result]

        scores = []
        for rid in reviewer_ids:
            score = await QualityScoring.compute_reviewer_score(db, rid, period_days)
            scores.append(score)

        # Sort by grade (A > B > C > D > F), then by avg_quality_score desc
        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
        scores.sort(key=lambda s: (grade_order.get(s["overall_grade"], 5), -s["avg_quality_score"]))
        return scores

    # ------------------------------------------------------------------
    # Asset quality
    # ------------------------------------------------------------------

    @staticmethod
    async def compute_asset_quality_score(
        db: AsyncSession,
        asset_id: UUID,
    ) -> dict[str, Any]:
        """Compute quality score for an asset based on all its review tasks."""
        result = await db.execute(
            select(ReviewTask)
            .options(selectinload(ReviewTask.reviews))
            .where(ReviewTask.asset_id == asset_id)
        )
        tasks = list(result.scalars().all())

        all_reviews = []
        all_scores = []
        consensus = True

        for task in tasks:
            for r in task.reviews:
                all_reviews.append({
                    "review_id": str(r.id),
                    "decision": r.decision.value,
                    "score": r.score,
                    "reviewer_id": str(r.reviewer_id),
                })
                if r.score is not None:
                    all_scores.append(r.score)

            # Check consensus within each task
            if len(task.reviews) >= 2:
                decisions = {r.decision.value for r in task.reviews}
                if len(decisions) > 1:
                    consensus = False

        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

        return {
            "score": round(avg_score, 2),
            "reviews": all_reviews,
            "consensus": consensus,
        }

    # ------------------------------------------------------------------
    # Quality trends
    # ------------------------------------------------------------------

    @staticmethod
    async def quality_trends(
        db: AsyncSession,
        workspace_id: UUID,
        period: str = "weekly",
    ) -> list[dict[str, Any]]:
        """Compute quality trends over time."""
        now = datetime.now(timezone.utc)

        if period == "daily":
            days_back = 30
            bucket_days = 1
        elif period == "monthly":
            days_back = 365
            bucket_days = 30
        else:  # weekly
            days_back = 90
            bucket_days = 7

        cutoff = now - timedelta(days=days_back)

        result = await db.execute(
            select(Review, ReviewTask)
            .join(ReviewTask, Review.task_id == ReviewTask.id)
            .where(
                and_(
                    ReviewTask.workspace_id == workspace_id,
                    Review.created_at >= cutoff,
                )
            )
            .order_by(Review.created_at)
        )
        rows = list(result.all())

        # Bucket into periods
        buckets: dict[str, dict] = defaultdict(
            lambda: {"scores": [], "count": 0, "sla_ok": 0, "total": 0}
        )

        for review, task in rows:
            if review.created_at:
                bucket_start = cutoff + timedelta(
                    days=((review.created_at - cutoff).days // bucket_days) * bucket_days
                )
                key = bucket_start.strftime("%Y-%m-%d")
                buckets[key]["count"] += 1
                buckets[key]["total"] += 1
                if review.score is not None:
                    buckets[key]["scores"].append(review.score)
                if review.created_at <= task.sla_deadline:
                    buckets[key]["sla_ok"] += 1

        trends = []
        for period_key in sorted(buckets.keys()):
            b = buckets[period_key]
            avg_score = sum(b["scores"]) / len(b["scores"]) if b["scores"] else 0.0
            sla_compliance = (b["sla_ok"] / b["total"] * 100) if b["total"] > 0 else 0.0
            trends.append({
                "period": period_key,
                "avg_score": round(avg_score, 2),
                "review_count": b["count"],
                "sla_compliance": round(sla_compliance, 2),
            })

        return trends
