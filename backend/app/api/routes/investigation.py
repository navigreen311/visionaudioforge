"""Investigation workspace API routes — case management, evidence, timeline,
collaboration, approvals, and report drafting."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.investigation.collaboration import CollaborationService
from app.services.investigation.reports import ReportService
from app.services.investigation.service import InvestigationService

router = APIRouter(prefix="/api/investigate", tags=["investigation"])

investigation_service = InvestigationService()
collaboration_service = CollaborationService()
report_service = ReportService()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateCaseRequest(BaseModel):
    name: str
    description: str
    workspace_id: UUID


class AddEvidenceRequest(BaseModel):
    asset_id: UUID
    notes: str
    timestamp: Optional[datetime] = None


class AddNoteRequest(BaseModel):
    user_id: str
    content: str


class AddCommentRequest(BaseModel):
    user_id: str
    content: str
    parent_id: Optional[UUID] = None


class CreateCheckpointRequest(BaseModel):
    user_id: str
    title: str
    description: str


class CreateApprovalRequest(BaseModel):
    user_id: str
    approver_id: str
    reason: str


class ProcessApprovalRequest(BaseModel):
    user_id: str
    decision: str  # 'approved' | 'rejected' | 'needs_revision'
    notes: Optional[str] = None


class ExportReportRequest(BaseModel):
    format: str = "markdown"


class SignReportRequest(BaseModel):
    user_id: str


def _serialize_event(e) -> dict:
    return {
        "id": str(e.id),
        "type": e.type,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "source": e.source,
        "payload": e.payload,
        "linked_asset_ids": [str(a) for a in (e.linked_asset_ids or [])],
        "workspace_id": str(e.workspace_id),
    }


# ---------------------------------------------------------------------------
# Case routes (existing)
# ---------------------------------------------------------------------------

@router.post("/cases", status_code=201)
async def create_case(body: CreateCaseRequest, db: AsyncSession = Depends(get_db)):
    """Create a new investigation case."""
    case = await investigation_service.create_case(
        db, name=body.name, description=body.description, workspace_id=body.workspace_id
    )
    return _serialize_event(case)


@router.get("/cases")
async def list_cases(
    workspace_id: UUID = Query(..., description="Workspace to list cases for"),
    db: AsyncSession = Depends(get_db),
):
    """List all investigation cases in a workspace."""
    cases = await investigation_service.list_cases(db, workspace_id)
    return [_serialize_event(c) for c in cases]


@router.get("/cases/{case_id}")
async def get_case(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a case with all linked evidence and notes."""
    try:
        data = await investigation_service.get_case(db, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "case": _serialize_event(data["case"]),
        "events": [_serialize_event(e) for e in data["events"]],
        "evidence": [_serialize_event(e) for e in data["evidence"]],
        "notes": [_serialize_event(e) for e in data["notes"]],
    }


@router.post("/cases/{case_id}/evidence", status_code=201)
async def add_evidence(
    case_id: UUID, body: AddEvidenceRequest, db: AsyncSession = Depends(get_db)
):
    """Add evidence (asset link) to a case."""
    try:
        evidence = await investigation_service.add_evidence(
            db,
            case_id=case_id,
            asset_id=body.asset_id,
            notes=body.notes,
            timestamp=body.timestamp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_event(evidence)


@router.post("/cases/{case_id}/notes", status_code=201)
async def add_note(
    case_id: UUID, body: AddNoteRequest, db: AsyncSession = Depends(get_db)
):
    """Add a note to a case."""
    try:
        note = await investigation_service.add_note(
            db, case_id=case_id, user_id=body.user_id, content=body.content
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_event(note)


@router.get("/timeline")
async def get_timeline(
    workspace_id: UUID = Query(...),
    start: datetime = Query(..., description="Start of time range"),
    end: datetime = Query(..., description="End of time range"),
    types: Optional[str] = Query(None, description="Comma-separated event types"),
    db: AsyncSession = Depends(get_db),
):
    """Query events timeline in a workspace within a time range."""
    event_types = types.split(",") if types else None
    events = await investigation_service.get_timeline(
        db,
        workspace_id=workspace_id,
        start_time=start,
        end_time=end,
        event_types=event_types,
    )
    return [_serialize_event(e) for e in events]


@router.get("/cases/{case_id}/export")
async def export_case(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """Export a full case as structured JSON."""
    try:
        return await investigation_service.export_case(db, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Collaboration routes
# ---------------------------------------------------------------------------

@router.post("/cases/{case_id}/comments", status_code=201)
async def add_comment(
    case_id: UUID, body: AddCommentRequest, db: AsyncSession = Depends(get_db)
):
    """Add a comment to a case (supports threaded replies via parent_id)."""
    try:
        comment = await collaboration_service.add_comment(
            db,
            case_id=case_id,
            user_id=body.user_id,
            content=body.content,
            parent_id=body.parent_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_event(comment)


@router.get("/cases/{case_id}/comments")
async def get_comments(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get threaded comments for a case."""
    return await collaboration_service.get_comments(db, case_id)


@router.post("/cases/{case_id}/checkpoint", status_code=201)
async def create_checkpoint(
    case_id: UUID, body: CreateCheckpointRequest, db: AsyncSession = Depends(get_db)
):
    """Create a review checkpoint on a case."""
    try:
        checkpoint = await collaboration_service.create_checkpoint(
            db,
            case_id=case_id,
            user_id=body.user_id,
            title=body.title,
            description=body.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_event(checkpoint)


@router.post("/cases/{case_id}/approval", status_code=201)
async def create_approval(
    case_id: UUID, body: CreateApprovalRequest, db: AsyncSession = Depends(get_db)
):
    """Request approval on a case."""
    try:
        approval = await collaboration_service.create_approval_request(
            db,
            case_id=case_id,
            user_id=body.user_id,
            approver_id=body.approver_id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_event(approval)


@router.post("/approvals/{approval_id}/process")
async def process_approval(
    approval_id: UUID, body: ProcessApprovalRequest, db: AsyncSession = Depends(get_db)
):
    """Process (approve/reject) an approval request."""
    try:
        result = await collaboration_service.process_approval(
            db,
            approval_id=approval_id,
            user_id=body.user_id,
            decision=body.decision,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_event(result)


@router.get("/approvals")
async def get_approval_queue(
    workspace_id: UUID = Query(...),
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get pending approval queue for a workspace."""
    return await collaboration_service.get_approval_queue(
        db, workspace_id=workspace_id, user_id=user_id
    )


# ---------------------------------------------------------------------------
# Report routes
# ---------------------------------------------------------------------------

@router.post("/cases/{case_id}/report")
async def generate_report(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """Generate a draft report from case data."""
    try:
        return await report_service.draft_report(db, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/cases/{case_id}/report/export")
async def export_report(
    case_id: UUID, body: ExportReportRequest, db: AsyncSession = Depends(get_db)
):
    """Export a report in the specified format (markdown, json, or pdf stub).

    When format is 'pdf', returns a text/plain stub indicating that full PDF
    generation is not yet implemented.
    """
    try:
        content = await report_service.export_report(db, case_id, format=body.format)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # PDF stub: return plain text instead of JSON
    if body.format == "pdf":
        return PlainTextResponse(
            content=content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="report_{case_id}.txt"'
            },
        )

    return {"content": content, "format": body.format}


@router.post("/cases/{case_id}/report/sign")
async def sign_report(
    case_id: UUID, body: SignReportRequest, db: AsyncSession = Depends(get_db)
):
    """Sign a report — creates audit record with content hash."""
    try:
        return await report_service.sign_report(db, case_id, user_id=body.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
