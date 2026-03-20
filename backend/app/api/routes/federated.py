"""Federated learning routes: federation lifecycle, rounds, and privacy."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_current_workspace, get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.services.federated.coordinator import FederatedCoordinator
from app.services.federated.privacy import DifferentialPrivacy

router = APIRouter(prefix="/federated", tags=["federated"])

_coordinator = FederatedCoordinator()
_privacy = DifferentialPrivacy()


# --- Request / Response Models ---


class CreateFederationRequest(BaseModel):
    name: str
    model_id: str
    config: dict | None = None


class JoinFederationRequest(BaseModel):
    participant_id: str
    participant_info: dict | None = None


class SubmitUpdateRequest(BaseModel):
    round_id: str
    participant_id: str
    model_update: dict
    metrics: dict | None = None


class StartRoundRequest(BaseModel):
    pass


class StopFederationRequest(BaseModel):
    pass


# --- Routes ---


@router.post("/create")
async def create_federation(
    req: CreateFederationRequest,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Create a new federated learning federation."""
    result = await _coordinator.create_federation(
        db,
        workspace_id=str(workspace.id),
        name=req.name,
        model_id=req.model_id,
        config=req.config,
    )
    return result


@router.post("/{federation_id}/join")
async def join_federation(
    federation_id: str,
    req: JoinFederationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Join an existing federation as a participant."""
    try:
        result = await _coordinator.join_federation(
            db, federation_id, req.participant_id, req.participant_info
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{federation_id}/start-round")
async def start_round(
    federation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Start a new training round for the federation."""
    try:
        result = await _coordinator.start_round(db, federation_id)
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )


@router.post("/{federation_id}/submit-update")
async def submit_update(
    federation_id: str,
    req: SubmitUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a participant's model update for the current round."""
    try:
        result = await _coordinator.submit_update(
            db, federation_id, req.round_id, req.participant_id, req.model_update, req.metrics
        )
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )


@router.post("/{federation_id}/aggregate")
async def aggregate_round(
    federation_id: str,
    round_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Aggregate all participant updates for a round."""
    try:
        result = await _coordinator.aggregate_round(db, federation_id, round_id)
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )


@router.get("/{federation_id}/status")
async def get_federation_status(
    federation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get current federation status, participants, and metrics."""
    try:
        result = await _coordinator.get_federation_status(db, federation_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{federation_id}/stop")
async def stop_federation(
    federation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Stop the federation and finalize results."""
    try:
        result = await _coordinator.stop_federation(db, federation_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{federation_id}/privacy")
async def privacy_report(
    federation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get privacy budget report for the federation."""
    try:
        fed = _coordinator._get_federation(federation_id)
        report = _privacy.privacy_report(
            federation_id=federation_id,
            epsilon_spent=fed["epsilon_spent"],
            epsilon_budget=fed["config"]["privacy_budget"],
            rounds_completed=fed["current_round"],
            max_rounds=fed["config"]["max_rounds"],
        )
        return report
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
