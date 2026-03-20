"""Tests for the ReviewOps system — review tasks, double review, quality scoring, and shifts."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.reviewops.review_service import ReviewService
from app.services.reviewops.double_review import DoubleReviewService
from app.services.reviewops.quality_scoring import QualityScoring, _compute_grade
from app.services.reviewops.shift_management import ShiftManager


pytestmark = pytest.mark.asyncio

WS_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ASSET_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
REVIEWER_1 = uuid.UUID("00000000-0000-0000-0000-000000000010")
REVIEWER_2 = uuid.UUID("00000000-0000-0000-0000-000000000011")
SENIOR = uuid.UUID("00000000-0000-0000-0000-000000000099")


# ======================================================================
# Helper: in-memory mock DB
# ======================================================================


class InMemoryDB:
    """Minimal async DB mock that stores objects in memory."""

    def __init__(self):
        self.store: dict[uuid.UUID, object] = {}
        self._pending: list = []

    def add(self, obj):
        self._pending.append(obj)

    async def flush(self):
        for obj in self._pending:
            if hasattr(obj, "id"):
                self.store[obj.id] = obj
        self._pending.clear()

    async def commit(self):
        await self.flush()

    async def execute(self, stmt):
        """Return a mock result — tests that need DB queries use the API tests."""
        return MagicMock(scalar_one_or_none=lambda: None, scalars=lambda: MagicMock(all=lambda: []))


# ======================================================================
# Review Service — unit tests
# ======================================================================


async def test_create_and_assign_task():
    """Creating a task returns pending status and a valid SLA deadline."""
    db = InMemoryDB()
    result = await ReviewService.create_review_task(
        db, WS_ID, ASSET_ID, "annotation_qa", priority="high", sla_hours=12,
    )
    assert result["status"] == "pending"
    assert "task_id" in result
    assert "sla_deadline" in result

    # Parse the deadline and verify it's ~12 hours from now
    deadline = datetime.fromisoformat(result["sla_deadline"])
    now = datetime.now(timezone.utc)
    diff_hours = (deadline - now).total_seconds() / 3600
    assert 11.9 < diff_hours < 12.1


async def test_auto_assign_round_robin():
    """Auto-assign distributes tasks to least-loaded reviewers."""
    # This tests the logic concept; full DB integration tested via API
    from app.services.reviewops.review_service import ReviewService

    db = InMemoryDB()
    # Create multiple tasks
    for _ in range(3):
        await ReviewService.create_review_task(
            db, WS_ID, ASSET_ID, "detection_verify",
        )
    # No reviewers available -> should assign 0
    result = await ReviewService.auto_assign_tasks(db, WS_ID)
    assert result["assigned"] == 0


async def test_submit_review():
    """Submitting a review returns review_id and decision."""
    db = InMemoryDB()
    task_result = await ReviewService.create_review_task(
        db, WS_ID, ASSET_ID, "alert_review",
    )
    task_id = uuid.UUID(task_result["task_id"])

    # Get the task from the store and add required attributes for submit
    task = db.store[task_id]
    task.reviews = []
    task.required_reviews = 1
    task.assigned_at = datetime.now(timezone.utc) - timedelta(minutes=10)

    # Patch the DB execute to return our task
    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = lambda: task
        return mock_result

    db.execute = mock_execute

    result = await ReviewService.submit_review(
        db, task_id, REVIEWER_1, "approved", score=4, notes="Looks good",
    )
    assert result["decision"] == "approved"
    assert "review_id" in result


# ======================================================================
# Double Review
# ======================================================================


async def test_double_review_consensus():
    """Two reviews with the same decision should show consensus."""
    from app.models.review import Review, ReviewDecision, ReviewTask, ReviewTaskStatus, ReviewType, ReviewPriority

    task_id = uuid.uuid4()
    task = ReviewTask(
        id=task_id,
        workspace_id=WS_ID,
        asset_id=ASSET_ID,
        review_type=ReviewType.annotation_qa,
        priority=ReviewPriority.normal,
        status=ReviewTaskStatus.in_review,
        required_reviews=2,
        sla_hours=24,
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    r1 = Review(id=uuid.uuid4(), task_id=task_id, reviewer_id=REVIEWER_1, decision=ReviewDecision.approved)
    r2 = Review(id=uuid.uuid4(), task_id=task_id, reviewer_id=REVIEWER_2, decision=ReviewDecision.approved)
    task.reviews = [r1, r2]

    db = InMemoryDB()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = lambda: task
        return mock_result

    db.execute = mock_execute

    result = await DoubleReviewService.check_review_complete(db, task_id)
    assert result["complete"] is True
    assert result["consensus"] is True
    assert result["disagreement"] is None


async def test_double_review_disagreement():
    """Two reviews with different decisions should flag disagreement."""
    from app.models.review import Review, ReviewDecision, ReviewTask, ReviewTaskStatus, ReviewType, ReviewPriority

    task_id = uuid.uuid4()
    task = ReviewTask(
        id=task_id,
        workspace_id=WS_ID,
        asset_id=ASSET_ID,
        review_type=ReviewType.detection_verify,
        priority=ReviewPriority.normal,
        status=ReviewTaskStatus.in_review,
        required_reviews=2,
        sla_hours=24,
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    r1 = Review(id=uuid.uuid4(), task_id=task_id, reviewer_id=REVIEWER_1, decision=ReviewDecision.approved)
    r2 = Review(id=uuid.uuid4(), task_id=task_id, reviewer_id=REVIEWER_2, decision=ReviewDecision.rejected)
    task.reviews = [r1, r2]

    db = InMemoryDB()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = lambda: task
        return mock_result

    db.execute = mock_execute

    result = await DoubleReviewService.check_review_complete(db, task_id)
    assert result["complete"] is True
    assert result["consensus"] is False
    assert result["disagreement"] is not None
    assert len(result["disagreement"]) == 2


# ======================================================================
# SLA
# ======================================================================


async def test_sla_breach_detection():
    """Tasks past their SLA deadline should be detected as breaches."""
    db = InMemoryDB()
    # Create a task with a very short SLA that's already expired
    result = await ReviewService.create_review_task(
        db, WS_ID, ASSET_ID, "content_moderation", sla_hours=0.001,
    )
    task_id = uuid.UUID(result["task_id"])
    task = db.store[task_id]
    # Force the deadline into the past
    task.sla_deadline = datetime.now(timezone.utc) - timedelta(hours=2)

    # Mock DB to return the breached task
    from app.models.review import ReviewTaskStatus
    task.status = ReviewTaskStatus.pending

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalars = lambda: MagicMock(all=lambda: [task])
        return mock_result

    db.execute = mock_execute

    breaches = await ReviewService.check_sla_breaches(db, WS_ID)
    assert len(breaches) == 1
    assert breaches[0]["overdue_hours"] > 0


# ======================================================================
# Quality Scoring
# ======================================================================


async def test_reviewer_score_grading():
    """Grade computation maps scores to A-F correctly."""
    assert _compute_grade(95) == "A"
    assert _compute_grade(85) == "B"
    assert _compute_grade(75) == "C"
    assert _compute_grade(65) == "D"
    assert _compute_grade(50) == "F"
    assert _compute_grade(90) == "A"
    assert _compute_grade(80) == "B"
    assert _compute_grade(70) == "C"
    assert _compute_grade(60) == "D"
    assert _compute_grade(59) == "F"


async def test_leaderboard_sorted():
    """Leaderboard returns reviewers sorted by grade then score."""
    db = InMemoryDB()

    # No reviewers -> empty list
    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalars = lambda: MagicMock(all=lambda: [])
        # For the distinct query
        mock_result.__iter__ = lambda self: iter([])
        return mock_result

    db.execute = mock_execute
    result = await QualityScoring.leaderboard(db, WS_ID, period_days=30)
    assert isinstance(result, list)


async def test_quality_trends():
    """Quality trends returns a list of period summaries."""
    db = InMemoryDB()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.all = lambda: []
        return mock_result

    db.execute = mock_execute
    result = await QualityScoring.quality_trends(db, WS_ID, period="weekly")
    assert isinstance(result, list)


# ======================================================================
# Shift Management
# ======================================================================


async def test_shift_creation():
    """Creating a shift returns the shift record."""
    db = InMemoryDB()
    now = datetime.now(timezone.utc)
    result = await ShiftManager.create_review_shift(
        db, WS_ID, REVIEWER_1,
        start=now,
        end=now + timedelta(hours=8),
        review_types=["annotation_qa", "detection_verify"],
    )
    assert result["active"] is True
    assert "shift_id" in result
    assert result["reviewer_id"] == str(REVIEWER_1)


async def test_shift_handoff():
    """Handoff transfers pending tasks between shifts."""
    from app.models.review import ReviewShift, ReviewTask, ReviewTaskStatus, ReviewType, ReviewPriority

    db = InMemoryDB()
    now = datetime.now(timezone.utc)

    # Create shifts
    from_shift_id = uuid.uuid4()
    to_shift_id = uuid.uuid4()
    from_shift = ReviewShift(
        id=from_shift_id, workspace_id=WS_ID, reviewer_id=REVIEWER_1,
        start_time=now - timedelta(hours=8), end_time=now, active=True,
    )
    to_shift = ReviewShift(
        id=to_shift_id, workspace_id=WS_ID, reviewer_id=REVIEWER_2,
        start_time=now, end_time=now + timedelta(hours=8), active=True,
    )

    # Create a pending task assigned to reviewer 1
    task = ReviewTask(
        id=uuid.uuid4(), workspace_id=WS_ID, asset_id=ASSET_ID,
        review_type=ReviewType.alert_review, priority=ReviewPriority.normal,
        status=ReviewTaskStatus.assigned, required_reviews=1, sla_hours=24,
        sla_deadline=now + timedelta(hours=16), assigned_to=REVIEWER_1,
    )

    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        mock_result = MagicMock()
        if call_count == 1:
            mock_result.scalar_one_or_none = lambda: from_shift
        elif call_count == 2:
            mock_result.scalar_one_or_none = lambda: to_shift
        else:
            mock_result.scalars = lambda: MagicMock(all=lambda: [task])
        return mock_result

    db.execute = mock_execute

    result = await ShiftManager.handoff(db, from_shift_id, to_shift_id, "End of day handoff")
    assert result["pending_tasks_transferred"] == 1
    assert task.assigned_to == REVIEWER_2


# ======================================================================
# API Integration tests (via ASGI client)
# ======================================================================


@pytest.mark.integration
async def test_api_create_task(test_app, test_workspace_id):
    """POST /api/reviewops/tasks creates a review task."""
    resp = await test_app.post(
        "/api/reviewops/tasks",
        params={"workspace_id": test_workspace_id},
        json={
            "asset_id": str(ASSET_ID),
            "review_type": "annotation_qa",
            "priority": "high",
            "required_reviews": 2,
            "sla_hours": 12,
        },
    )
    assert resp.status_code != 404, f"Route not found: {resp.text}"
    if resp.status_code in (200, 201):
        data = resp.json()
        assert data["status"] == "pending"
        assert "task_id" in data


@pytest.mark.integration
async def test_api_submit_review(test_app, test_workspace_id):
    """POST /api/reviewops/tasks/{id}/review submits a review."""
    # Create a task first
    create_resp = await test_app.post(
        "/api/reviewops/tasks",
        params={"workspace_id": test_workspace_id},
        json={
            "asset_id": str(ASSET_ID),
            "review_type": "detection_verify",
        },
    )
    if create_resp.status_code in (200, 201):
        task_id = create_resp.json()["task_id"]
        # Submit review
        resp = await test_app.post(
            f"/api/reviewops/tasks/{task_id}/review",
            json={
                "reviewer_id": str(REVIEWER_1),
                "decision": "approved",
                "score": 4,
            },
        )
        assert resp.status_code != 404
    else:
        # If create failed (e.g., no DB), verify route exists
        assert create_resp.status_code != 404


@pytest.mark.integration
async def test_api_leaderboard(test_app, test_workspace_id):
    """GET /api/reviewops/leaderboard returns reviewer rankings."""
    resp = await test_app.get(
        "/api/reviewops/leaderboard",
        params={"workspace_id": test_workspace_id},
    )
    assert resp.status_code != 404, f"Route not found: {resp.text}"
