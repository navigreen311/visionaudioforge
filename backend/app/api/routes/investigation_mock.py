"""Investigation page API routes — mock endpoints for the Investigate UI.

Provides realistic stub data for cases, events, comments, approvals,
and report export.  These run without a database and are meant to
unblock frontend development.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Path
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/investigation", tags=["investigation-mock"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)


def _ts(delta_hours: int = 0) -> str:
    return (_NOW - timedelta(hours=delta_hours)).isoformat()


def _uid() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateCaseRequest(BaseModel):
    title: str
    priority: str = "medium"
    assignee: str = "unassigned"
    description: str = ""


class CreateEventRequest(BaseModel):
    type: str
    summary: str
    severity: str = "info"
    media_b64: Optional[str] = None


class CreateCommentRequest(BaseModel):
    author: str
    text: str


class CreateApprovalRequest(BaseModel):
    requester: str
    reason: str = ""
    deadline: Optional[str] = None


class ExportReportRequest(BaseModel):
    format: str = "text"


# ---------------------------------------------------------------------------
# Mock data factories
# ---------------------------------------------------------------------------

_CASE_IDS = [_uid(), _uid(), _uid()]


def _mock_cases() -> list[dict]:
    return [
        {
            "id": _CASE_IDS[0],
            "title": "Unauthorized perimeter access detected",
            "priority": "high",
            "status": "open",
            "assignee": "alice@vison.ai",
            "event_count": 12,
            "created_at": _ts(48),
        },
        {
            "id": _CASE_IDS[1],
            "title": "Audio anomaly in sector B-7",
            "priority": "medium",
            "status": "in_progress",
            "assignee": "bob@vison.ai",
            "event_count": 5,
            "created_at": _ts(24),
        },
        {
            "id": _CASE_IDS[2],
            "title": "Routine safety review — Q1 2026",
            "priority": "low",
            "status": "closed",
            "assignee": "carol@vison.ai",
            "event_count": 3,
            "created_at": _ts(168),
        },
    ]


def _mock_events(case_id: str) -> list[dict]:
    return [
        {
            "id": _uid(),
            "type": "motion_detected",
            "timestamp": _ts(47),
            "summary": "Motion sensor triggered at gate A-3",
            "severity": "high",
            "media_b64": None,
        },
        {
            "id": _uid(),
            "type": "audio_alert",
            "timestamp": _ts(46),
            "summary": "Anomalous frequency spike captured by mic #4",
            "severity": "medium",
            "media_b64": None,
        },
        {
            "id": _uid(),
            "type": "camera_snapshot",
            "timestamp": _ts(45),
            "summary": "Snapshot from Camera NW-12 saved to evidence",
            "severity": "low",
            "media_b64": None,
        },
        {
            "id": _uid(),
            "type": "access_log",
            "timestamp": _ts(44),
            "summary": "Badge scan by unknown ID at door B-1",
            "severity": "high",
            "media_b64": None,
        },
        {
            "id": _uid(),
            "type": "operator_note",
            "timestamp": _ts(43),
            "summary": "Operator flagged footage for manual review",
            "severity": "info",
            "media_b64": None,
        },
    ]


def _mock_comments(case_id: str) -> list[dict]:
    return [
        {
            "id": _uid(),
            "author": "alice@vison.ai",
            "text": "I reviewed the footage — confirmed unauthorized entry at 02:14 UTC.",
            "created_at": _ts(40),
            "reactions": {"thumbsup": 2},
        },
        {
            "id": _uid(),
            "author": "bob@vison.ai",
            "text": "Audio analysis matches a vehicle engine signature. Running MFCC comparison now.",
            "created_at": _ts(38),
            "reactions": {},
        },
        {
            "id": _uid(),
            "author": "carol@vison.ai",
            "text": "Escalating to security lead for approval before exporting the report.",
            "created_at": _ts(36),
            "reactions": {"thumbsup": 1, "eyes": 1},
        },
    ]


def _mock_approvals(case_id: str) -> list[dict]:
    return [
        {
            "id": _uid(),
            "status": "pending",
            "requester": "carol@vison.ai",
            "deadline": _ts(-24),  # 24 hours in the future
        },
        {
            "id": _uid(),
            "status": "approved",
            "requester": "alice@vison.ai",
            "deadline": _ts(12),
        },
    ]


# ---------------------------------------------------------------------------
# Routes — Cases
# ---------------------------------------------------------------------------

@router.get("/cases")
async def list_cases():
    """Return mock investigation cases."""
    return _mock_cases()


@router.post("/cases", status_code=201)
async def create_case(body: CreateCaseRequest):
    """Accept a new case and return it with generated fields."""
    return {
        "id": _uid(),
        "title": body.title,
        "priority": body.priority,
        "status": "open",
        "assignee": body.assignee,
        "event_count": 0,
        "created_at": _ts(0),
    }


# ---------------------------------------------------------------------------
# Routes — Events
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/events")
async def list_events(case_id: str = Path(...)):
    """Return mock events for a case."""
    return _mock_events(case_id)


@router.post("/cases/{case_id}/events", status_code=201)
async def create_event(body: CreateEventRequest, case_id: str = Path(...)):
    """Accept a new event and return it with generated fields."""
    return {
        "id": _uid(),
        "type": body.type,
        "timestamp": _ts(0),
        "summary": body.summary,
        "severity": body.severity,
        "media_b64": body.media_b64,
    }


# ---------------------------------------------------------------------------
# Routes — Comments
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/comments")
async def list_comments(case_id: str = Path(...)):
    """Return mock comments for a case."""
    return _mock_comments(case_id)


@router.post("/cases/{case_id}/comments", status_code=201)
async def create_comment(body: CreateCommentRequest, case_id: str = Path(...)):
    """Accept a new comment and return it with generated fields."""
    return {
        "id": _uid(),
        "author": body.author,
        "text": body.text,
        "created_at": _ts(0),
        "reactions": {},
    }


# ---------------------------------------------------------------------------
# Routes — Approvals
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/approvals")
async def list_approvals(case_id: str = Path(...)):
    """Return mock approvals for a case."""
    return _mock_approvals(case_id)


@router.post("/cases/{case_id}/approvals", status_code=201)
async def create_approval(body: CreateApprovalRequest, case_id: str = Path(...)):
    """Accept an approval request and return it with generated fields."""
    return {
        "id": _uid(),
        "status": "pending",
        "requester": body.requester,
        "deadline": body.deadline or _ts(-48),
    }


# ---------------------------------------------------------------------------
# Routes — Report export
# ---------------------------------------------------------------------------

@router.post("/cases/{case_id}/report/export")
async def export_report(case_id: str = Path(...)):
    """Return a plain-text placeholder report for the case."""
    report = (
        "INVESTIGATION REPORT\n"
        "====================\n"
        f"Case ID: {case_id}\n"
        f"Generated: {_ts(0)}\n\n"
        "Summary:\n"
        "  This is a placeholder investigation report.  In production this\n"
        "  will aggregate all evidence, timeline events, analyst comments,\n"
        "  and approval chain into a formatted document.\n\n"
        "Status: DRAFT\n"
    )
    return PlainTextResponse(content=report, media_type="text/plain")
