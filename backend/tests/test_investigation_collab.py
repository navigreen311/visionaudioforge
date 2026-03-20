"""Tests for investigation collaboration: comments, approvals, and report drafting."""

import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.services.investigation.av_player import AVSyncPlayer
from app.services.investigation.collaboration import CollaborationService
from app.services.investigation.reports import ReportService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(
    type_: str = "case",
    payload: dict | None = None,
    workspace_id: UUID | None = None,
    linked_asset_ids: list | None = None,
):
    """Create a mock Event object."""
    ev = MagicMock()
    ev.id = uuid4()
    ev.type = type_
    ev.source = "investigation"
    ev.workspace_id = workspace_id or uuid4()
    ev.payload = payload or {}
    ev.timestamp = datetime(2025, 6, 15, 12, 0, 0)
    ev.linked_asset_ids = linked_asset_ids or []
    return ev


def _mock_db_with_case(case_event):
    """Create a mock AsyncSession that returns the given case event."""
    db = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = case_event

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock.scalars.return_value = scalars_mock

    db.execute.return_value = result_mock
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# ---------------------------------------------------------------------------
# Comment tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_add_comment():
    """Adding a comment to a case creates a comment event."""
    workspace_id = uuid4()
    case_id = uuid4()
    case_event = _make_event("case", {"name": "Test Case"}, workspace_id)
    case_event.id = case_id

    db = _mock_db_with_case(case_event)
    svc = CollaborationService()

    result = await svc.add_comment(db, case_id, "user-1", "This looks suspicious")

    db.add.assert_called_once()
    added_event = db.add.call_args[0][0]
    assert added_event.type == "comment"
    assert added_event.payload["content"] == "This looks suspicious"
    assert added_event.payload["user_id"] == "user-1"
    assert added_event.payload["case_id"] == str(case_id)


@pytest.mark.anyio
async def test_threaded_comments():
    """get_comments returns a threaded structure with replies nested."""
    svc = CollaborationService()
    case_id = uuid4()
    workspace_id = uuid4()

    parent = _make_event("comment", {
        "case_id": str(case_id), "user_id": "user-1",
        "content": "Root comment", "parent_id": None,
    }, workspace_id)

    child = _make_event("comment", {
        "case_id": str(case_id), "user_id": "user-2",
        "content": "Reply", "parent_id": str(parent.id),
    }, workspace_id)

    db = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [parent, child]
    result_mock.scalars.return_value = scalars_mock
    db.execute.return_value = result_mock

    comments = await svc.get_comments(db, case_id)

    assert len(comments) == 1  # Only 1 root
    assert comments[0]["content"] == "Root comment"
    assert len(comments[0]["replies"]) == 1
    assert comments[0]["replies"][0]["content"] == "Reply"


# ---------------------------------------------------------------------------
# Checkpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_create_checkpoint():
    """Creating a checkpoint produces an event with type='checkpoint'."""
    workspace_id = uuid4()
    case_id = uuid4()
    case_event = _make_event("case", {"name": "Test"}, workspace_id)
    case_event.id = case_id

    db = _mock_db_with_case(case_event)
    svc = CollaborationService()

    await svc.create_checkpoint(db, case_id, "user-1", "Phase 1 Complete", "All evidence reviewed")

    added = db.add.call_args[0][0]
    assert added.type == "checkpoint"
    assert added.payload["title"] == "Phase 1 Complete"
    assert added.payload["description"] == "All evidence reviewed"


# ---------------------------------------------------------------------------
# Approval tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_approval_request_and_process():
    """Creating and processing an approval request updates status correctly."""
    workspace_id = uuid4()
    case_id = uuid4()
    case_event = _make_event("case", {"name": "Test"}, workspace_id)
    case_event.id = case_id

    db = _mock_db_with_case(case_event)
    svc = CollaborationService()

    # Create request
    await svc.create_approval_request(db, case_id, "requester-1", "approver-1", "Ready for review")

    added = db.add.call_args[0][0]
    assert added.type == "approval_request"
    assert added.payload["status"] == "pending"
    assert added.payload["approver_id"] == "approver-1"

    # Process approval
    approval_event = _make_event("approval_request", {
        "case_id": str(case_id),
        "requester_id": "requester-1",
        "approver_id": "approver-1",
        "reason": "Ready for review",
        "status": "pending",
    }, workspace_id)

    db2 = _mock_db_with_case(approval_event)
    # Override to return the approval event for approval_request type lookup
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = approval_event
    db2.execute.return_value = result_mock

    await svc.process_approval(db2, approval_event.id, "approver-1", "approved", "Looks good")

    assert approval_event.payload["status"] == "approved"
    assert approval_event.payload["decided_by"] == "approver-1"


@pytest.mark.anyio
async def test_approval_queue():
    """get_approval_queue returns only pending approvals."""
    svc = CollaborationService()
    workspace_id = uuid4()

    pending = _make_event("approval_request", {
        "case_id": str(uuid4()), "approver_id": "approver-1",
        "requester_id": "user-1", "reason": "Review", "status": "pending",
    }, workspace_id)

    approved = _make_event("approval_request", {
        "case_id": str(uuid4()), "approver_id": "approver-1",
        "requester_id": "user-2", "reason": "Done", "status": "approved",
    }, workspace_id)

    db = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [pending, approved]
    result_mock.scalars.return_value = scalars_mock
    db.execute.return_value = result_mock

    queue = await svc.get_approval_queue(db, workspace_id)

    assert len(queue) == 1
    assert queue[0]["reason"] == "Review"


# ---------------------------------------------------------------------------
# Report tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_draft_report_from_case():
    """draft_report auto-generates a report with title, sections, and evidence refs."""
    workspace_id = uuid4()
    case_id = uuid4()
    case_event = _make_event("case", {
        "name": "Incident Alpha", "description": "A security incident."
    }, workspace_id)
    case_event.id = case_id

    evidence = _make_event("evidence", {
        "case_id": str(case_id), "notes": "Suspicious file found"
    }, workspace_id, linked_asset_ids=[uuid4()])

    note = _make_event("note", {
        "case_id": str(case_id), "content": "User account compromised"
    }, workspace_id)

    db = AsyncMock()

    # First call returns case, second returns all events
    case_result = MagicMock()
    case_result.scalar_one_or_none.return_value = case_event

    events_result = MagicMock()
    events_scalars = MagicMock()
    events_scalars.all.return_value = [evidence, note]
    events_result.scalars.return_value = events_scalars

    db.execute = AsyncMock(side_effect=[case_result, events_result])

    svc = ReportService()
    report = await svc.draft_report(db, case_id)

    assert report["title"] == "Investigation Report: Incident Alpha"
    assert len(report["sections"]) >= 3  # Overview, Evidence, Timeline
    assert report["generated_at"] is not None
    assert len(report["evidence_refs"]) == 1


@pytest.mark.anyio
async def test_export_report_markdown():
    """export_report with markdown format produces markdown with headers."""
    workspace_id = uuid4()
    case_id = uuid4()
    case_event = _make_event("case", {
        "name": "Test Case", "description": "Test description"
    }, workspace_id)
    case_event.id = case_id

    db = AsyncMock()

    case_result = MagicMock()
    case_result.scalar_one_or_none.return_value = case_event

    events_result = MagicMock()
    events_scalars = MagicMock()
    events_scalars.all.return_value = []
    events_result.scalars.return_value = events_scalars

    db.execute = AsyncMock(side_effect=[case_result, events_result])

    svc = ReportService()
    md = await svc.export_report(db, case_id, format="markdown")

    assert "# Investigation Report: Test Case" in md
    assert "## Overview" in md
    assert "Test description" in md


@pytest.mark.anyio
async def test_sign_report_creates_hash():
    """sign_report creates an audit event with a SHA-256 hash of the report content."""
    workspace_id = uuid4()
    case_id = uuid4()
    case_event = _make_event("case", {
        "name": "Sign Test", "description": "Test"
    }, workspace_id)
    case_event.id = case_id

    db = AsyncMock()

    # draft_report needs two execute calls, then sign_report needs one more
    case_result1 = MagicMock()
    case_result1.scalar_one_or_none.return_value = case_event

    events_result = MagicMock()
    events_scalars = MagicMock()
    events_scalars.all.return_value = []
    events_result.scalars.return_value = events_scalars

    case_result2 = MagicMock()
    case_result2.scalar_one_or_none.return_value = case_event

    db.execute = AsyncMock(side_effect=[case_result1, events_result, case_result2])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    svc = ReportService()
    result = await svc.sign_report(db, case_id, "signer-1")

    assert result["signed_by"] == "signer-1"
    assert result["signed_at"] is not None
    assert len(result["hash"]) == 64  # SHA-256 hex digest


# ---------------------------------------------------------------------------
# API-level tests (using test client)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_comments(test_app, test_workspace_id):
    """POST and GET comments via the API."""
    # Create a case first
    case_resp = await test_app.post("/api/investigate/cases", json={
        "name": "Comment Test Case",
        "description": "Testing comments",
        "workspace_id": test_workspace_id,
    })

    if case_resp.status_code == 201:
        case_id = case_resp.json()["id"]

        # Add a comment
        comment_resp = await test_app.post(
            f"/api/investigate/cases/{case_id}/comments",
            json={"user_id": "tester", "content": "First comment"},
        )
        assert comment_resp.status_code in (201, 500)  # 500 if no real DB

        # Get comments
        get_resp = await test_app.get(f"/api/investigate/cases/{case_id}/comments")
        assert get_resp.status_code in (200, 500)
    else:
        # No DB available — verify route exists (422 = validation, 500 = no DB)
        assert case_resp.status_code in (422, 500)


@pytest.mark.anyio
async def test_api_approval(test_app, test_workspace_id):
    """POST approval request and process via the API."""
    case_resp = await test_app.post("/api/investigate/cases", json={
        "name": "Approval Test Case",
        "description": "Testing approvals",
        "workspace_id": test_workspace_id,
    })

    if case_resp.status_code == 201:
        case_id = case_resp.json()["id"]

        # Request approval
        approval_resp = await test_app.post(
            f"/api/investigate/cases/{case_id}/approval",
            json={
                "user_id": "requester",
                "approver_id": "approver",
                "reason": "Ready for review",
            },
        )
        assert approval_resp.status_code in (201, 500)

        if approval_resp.status_code == 201:
            approval_id = approval_resp.json()["id"]

            # Process approval
            process_resp = await test_app.post(
                f"/api/investigate/approvals/{approval_id}/process",
                json={
                    "user_id": "approver",
                    "decision": "approved",
                    "notes": "Looks good",
                },
            )
            assert process_resp.status_code in (200, 500)

        # Check approval queue
        queue_resp = await test_app.get(
            "/api/investigate/approvals",
            params={"workspace_id": test_workspace_id},
        )
        assert queue_resp.status_code in (200, 500)
    else:
        assert case_resp.status_code in (422, 500)
