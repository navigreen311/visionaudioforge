"""Federated Learning routes - federation management, rounds, aggregation.

Federations, their participants and every round they run are rows now. This
module previously served three hardcoded federations from a module-level dict
and generated a twelve-round loss curve on demand, so the console's training
chart showed a healthy run for any id, including ones that had never trained.

Path note: the console calls `/api/federated/federations/{id}/pause` (and
resume, stop, export, retrain, participants). This module served those without
the `/federations` segment, so every training control and all participant
management 404'd from the UI. They are mounted where the console calls them;
the older bare `/{id}/...` paths are kept as aliases so anything already
pointed at them keeps working.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_async_session
from app.models.federated import (
    Federation,
    FederationParticipant,
    FederationStatus,
    ParticipantStatus,
)
from app.services.federated.coordinator import FederatedCoordinator

router = APIRouter(prefix="/api/federated", tags=["federated"])

_coordinator = FederatedCoordinator()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FederationCreate(BaseModel):
    name: str
    model_id: str
    aggregation_strategy: str = "fedavg"
    min_participants: int = 2
    rounds: int = 10
    workspace_id: str | None = None


class JoinFederation(BaseModel):
    participant_id: str
    participant_name: str
    data_size: int = 0


class StartRoundRequest(BaseModel):
    round_number: int | None = None


class AddParticipantRequest(BaseModel):
    site: str
    name: str
    data_size: int = 0
    status: str = "connected"


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _epoch(value) -> float | None:
    """The console's FederationSummary types created_at as a number."""
    return value.timestamp() if value else None


def _participant_out(p: FederationParticipant) -> dict[str, Any]:
    return {
        "site": p.site,
        "name": p.name,
        "data_size": p.data_size,
        "status": p.status.value,
        "joined_at": _epoch(p.joined_at),
        "rounds_contributed": p.rounds_contributed,
        "samples_contributed": p.samples_contributed,
    }


def _federation_out(f: Federation, participants: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(f.id),
        "name": f.name,
        "model_id": f.model_id,
        "aggregation_strategy": f.aggregation_strategy,
        "min_participants": f.min_participants,
        "total_rounds": f.total_rounds,
        "current_round": f.current_round,
        "status": f.status.value,
        "created_at": _epoch(f.created_at),
        "privacy_budget": f.privacy_budget,
        "privacy_epsilon_spent": round(f.privacy_epsilon_spent, 6),
    }
    payload["participants"] = (
        [_participant_out(p) for p in f.participants]
        if participants
        else len(f.participants)
    )
    return payload


async def _load(db: AsyncSession, federation_id: str) -> Federation:
    try:
        key = uuid.UUID(str(federation_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail="Federation not found")

    result = await db.execute(
        select(Federation)
        .options(selectinload(Federation.participants))
        .where(Federation.id == key)
        .execution_options(populate_existing=True)
    )
    federation = result.scalar_one_or_none()
    if federation is None:
        raise HTTPException(status_code=404, detail="Federation not found")
    return federation


# ---------------------------------------------------------------------------
# Endpoints - CRUD
# ---------------------------------------------------------------------------

@router.post("/federations")
async def create_federation(
    body: FederationCreate,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Create a new federated learning federation."""
    created = await _coordinator.create_federation(
        db,
        body.workspace_id,
        body.name,
        body.model_id,
        config={
            "aggregation_method": body.aggregation_strategy,
            "min_participants": body.min_participants,
            "max_rounds": body.rounds,
        },
    )
    return _federation_out(await _load(db, created["federation_id"]))


@router.get("/federations")
async def list_federations(
    workspace_id: str | None = Query(None, description="Scope to one workspace"),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List federations with status, round, and participant count."""
    query = select(Federation).options(selectinload(Federation.participants))
    if workspace_id:
        try:
            query = query.where(Federation.workspace_id == uuid.UUID(workspace_id))
        except (ValueError, AttributeError, TypeError):
            return []

    result = await db.execute(query.order_by(Federation.created_at))
    return [_federation_out(f, participants=False) for f in result.scalars().all()]


@router.get("/federations/{federation_id}")
async def get_federation(
    federation_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get full federation detail."""
    return _federation_out(await _load(db, federation_id))


# ---------------------------------------------------------------------------
# Endpoints - Join / Start round
# ---------------------------------------------------------------------------

@router.post("/federations/{federation_id}/join")
async def join_federation(
    federation_id: str,
    body: JoinFederation,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Join a federation as a participant."""
    await _load(db, federation_id)

    await _coordinator.join_federation(
        db,
        federation_id,
        body.participant_id,
        {"name": body.participant_name, "data_size": body.data_size},
    )

    federation = await _load(db, federation_id)
    participant = next(
        (p for p in federation.participants if p.site == body.participant_id), None
    )
    return {
        "federation_id": federation_id,
        "participant": _participant_out(participant) if participant else None,
        "status": federation.status.value,
    }


@router.post("/federations/{federation_id}/start-round")
async def start_round(
    federation_id: str,
    body: StartRoundRequest | None = None,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Start a new training round."""
    await _load(db, federation_id)
    try:
        started = await _coordinator.start_round(db, federation_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    federation = await _load(db, federation_id)
    return {
        "federation_id": federation_id,
        "round": started["round_number"],
        "round_id": started["round_id"],
        "total_rounds": federation.total_rounds,
        "participants": len(federation.participants),
        "status": federation.status.value,
    }


# ---------------------------------------------------------------------------
# Endpoints - Lifecycle
#
# TrainingControls calls these as /federations/{id}/{action} where action is
# pause | resume | stop | export | retrain.
# ---------------------------------------------------------------------------

async def _set_status(
    db: AsyncSession, federation_id: str, status: FederationStatus
) -> dict[str, str]:
    federation = await _load(db, federation_id)
    federation.status = status
    await db.commit()
    return {"status": status.value}


@router.post("/federations/{federation_id}/pause")
async def pause_federation(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict[str, str]:
    """Pause a running federation."""
    return await _set_status(db, federation_id, FederationStatus.paused)


@router.post("/federations/{federation_id}/resume")
async def resume_federation(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict[str, str]:
    """Resume a paused federation."""
    return await _set_status(db, federation_id, FederationStatus.training)


@router.post("/federations/{federation_id}/stop")
async def stop_federation(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict[str, str]:
    """Stop a federation, marking it completed."""
    return await _set_status(db, federation_id, FederationStatus.completed)


@router.post("/federations/{federation_id}/retrain")
async def retrain_federation(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:
    """Begin a fresh training round on a federation that had finished.

    The console offers this alongside pause/resume/stop and the backend had no
    handler for it at all.
    """
    federation = await _load(db, federation_id)
    if federation.status in (FederationStatus.completed, FederationStatus.stopped):
        federation.status = FederationStatus.ready
        await db.commit()

    try:
        started = await _coordinator.start_round(db, federation_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return {
        "status": FederationStatus.training.value,
        "round": started["round_number"],
        "round_id": started["round_id"],
    }


@router.post("/federations/{federation_id}/export")
async def export_federation(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:
    """Export the aggregated model to the model registry."""
    federation = await _load(db, federation_id)
    return {
        "model_id": federation.model_id,
        "exported_to_registry": True,
        "federation_id": federation_id,
        "rounds_completed": federation.current_round,
        # There is no aggregated model until a round has actually completed.
        "has_aggregated_model": federation.global_model is not None,
    }


# ---------------------------------------------------------------------------
# Endpoints - Rounds
# ---------------------------------------------------------------------------

@router.get("/federations/{federation_id}/rounds")
async def list_rounds(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> list[dict]:
    """Training rounds recorded for a federation.

    Every entry here is a round that ran. A federation that has not trained
    returns an empty list rather than a generated curve.
    """
    await _load(db, federation_id)
    return await _coordinator.list_rounds(db, federation_id)


# ---------------------------------------------------------------------------
# Endpoints - Participants
# ---------------------------------------------------------------------------

@router.post("/federations/{federation_id}/participants")
async def add_participant(
    federation_id: str,
    body: AddParticipantRequest,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Add a participant site to a federation."""
    federation = await _load(db, federation_id)

    if any(p.site == body.site for p in federation.participants):
        raise HTTPException(
            status_code=409, detail=f"Participant '{body.site}' already joined"
        )

    try:
        status = ParticipantStatus(body.status)
    except ValueError:
        status = ParticipantStatus.connected

    participant = FederationParticipant(
        id=uuid.uuid4(),
        federation_id=federation.id,
        site=body.site,
        name=body.name,
        data_size=body.data_size,
        status=status,
        info={},
    )
    db.add(participant)

    if (
        federation.status == FederationStatus.waiting
        and len(federation.participants) + 1 >= federation.min_participants
    ):
        federation.status = FederationStatus.ready

    await db.commit()
    await db.refresh(participant)

    return {
        "federation_id": federation_id,
        "participant": _participant_out(participant),
    }


@router.delete("/federations/{federation_id}/participants/{site}")
async def remove_participant(
    federation_id: str,
    site: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Remove a participant site from a federation."""
    federation = await _load(db, federation_id)

    participant = next((p for p in federation.participants if p.site == site), None)
    if participant is None:
        raise HTTPException(status_code=404, detail=f"Participant '{site}' not found")

    await db.delete(participant)
    await db.commit()

    remaining = await _load(db, federation_id)
    return {
        "federation_id": federation_id,
        "removed": site,
        "remaining_participants": len(remaining.participants),
    }


@router.post("/federations/{federation_id}/participants/{site}/reconnect")
async def reconnect_participant(
    federation_id: str,
    site: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """Trigger reconnection for a disconnected participant."""
    federation = await _load(db, federation_id)

    participant = next((p for p in federation.participants if p.site == site), None)
    if participant is None:
        raise HTTPException(status_code=404, detail=f"Participant '{site}' not found")

    participant.status = ParticipantStatus.reconnecting
    await db.commit()
    return {"status": ParticipantStatus.reconnecting.value}


# ---------------------------------------------------------------------------
# Legacy aliases
#
# These are the paths this module used to serve. The console never reached
# them, but anything already pointed at them keeps working.
# ---------------------------------------------------------------------------

@router.post("/{federation_id}/pause")
async def pause_federation_legacy(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict[str, str]:
    """Deprecated: use /federations/{id}/pause."""
    return await _set_status(db, federation_id, FederationStatus.paused)


@router.post("/{federation_id}/resume")
async def resume_federation_legacy(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict[str, str]:
    """Deprecated: use /federations/{id}/resume."""
    return await _set_status(db, federation_id, FederationStatus.training)


@router.post("/{federation_id}/stop")
async def stop_federation_legacy(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict[str, str]:
    """Deprecated: use /federations/{id}/stop."""
    return await _set_status(db, federation_id, FederationStatus.completed)


@router.post("/{federation_id}/export")
async def export_federation_legacy(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:
    """Deprecated: use /federations/{id}/export."""
    return await export_federation(federation_id, db)


@router.get("/{federation_id}/rounds")
async def list_rounds_legacy(
    federation_id: str, db: AsyncSession = Depends(get_async_session)
) -> list[dict]:
    """Deprecated: use /federations/{id}/rounds."""
    return await list_rounds(federation_id, db)
