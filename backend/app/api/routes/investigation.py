"""Investigation workspace API routes — case management, evidence, timeline."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.investigation.service import InvestigationService

router = APIRouter(prefix="/api/investigate", tags=["investigation"])

investigation_service = InvestigationService()


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
# Routes
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
