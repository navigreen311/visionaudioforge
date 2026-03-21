"""Federated Learning routes — federation management, rounds, aggregation."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/federated", tags=["federated"])


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
    site_id: str
    site_name: str
    location: str = ""
    connection_url: str = ""


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_federations: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/federations")
async def create_federation(body: FederationCreate) -> dict[str, Any]:
    """Create a new federated learning federation."""
    fid = str(uuid.uuid4())
    federation = {
        "id": fid,
        "name": body.name,
        "model_id": body.model_id,
        "aggregation_strategy": body.aggregation_strategy,
        "min_participants": body.min_participants,
        "total_rounds": body.rounds,
        "current_round": 0,
        "status": "waiting",
        "participants": [],
        "created_at": time.time(),
    }
    _federations[fid] = federation
    return federation


@router.get("/federations")
async def list_federations() -> list[dict]:
    """List all federations."""
    return list(_federations.values())


@router.get("/federations/{federation_id}")
async def get_federation(federation_id: str) -> dict:
    if federation_id not in _federations:
        raise HTTPException(status_code=404, detail="Federation not found")
    return _federations[federation_id]


@router.post("/federations/{federation_id}/join")
async def join_federation(federation_id: str, body: JoinFederation) -> dict[str, Any]:
    """Join a federation as a participant."""
    if federation_id not in _federations:
        raise HTTPException(status_code=404, detail="Federation not found")
    fed = _federations[federation_id]
    participant = {
        "id": body.participant_id,
        "name": body.participant_name,
        "data_size": body.data_size,
        "joined_at": time.time(),
    }
    fed["participants"].append(participant)
    if len(fed["participants"]) >= fed["min_participants"]:
        fed["status"] = "ready"
    return {"federation_id": federation_id, "participant": participant, "status": fed["status"]}


@router.post("/federations/{federation_id}/start-round")
async def start_round(federation_id: str, body: StartRoundRequest | None = None) -> dict[str, Any]:
    """Start a new training round."""
    if federation_id not in _federations:
        raise HTTPException(status_code=404, detail="Federation not found")
    fed = _federations[federation_id]
    fed["current_round"] += 1
    fed["status"] = "training"
    return {
        "federation_id": federation_id,
        "round": fed["current_round"],
        "total_rounds": fed["total_rounds"],
        "participants": len(fed["participants"]),
        "status": "training",
    }


# ---------------------------------------------------------------------------
# Participant management endpoints
# ---------------------------------------------------------------------------

@router.post("/federations/{federation_id}/participants")
async def add_participant(
    federation_id: str, body: AddParticipantRequest
) -> dict[str, str | dict[str, str | float]]:
    """Invite / add a participant site to a federation."""
    if federation_id not in _federations:
        raise HTTPException(status_code=404, detail="Federation not found")

    fed = _federations[federation_id]
    # Check for duplicate site_id
    for p in fed["participants"]:
        if p["id"] == body.site_id:
            raise HTTPException(
                status_code=409, detail=f"Participant {body.site_id} already exists"
            )

    participant = {
        "id": body.site_id,
        "name": body.site_name,
        "location": body.location,
        "connection_url": body.connection_url,
        "status": "idle",
        "samples": 0,
        "contribution_pct": 0.0,
        "local_accuracy": 0.0,
        "data_quality": 0.0,
        "joined_at": time.time(),
    }
    fed["participants"].append(participant)

    if len(fed["participants"]) >= fed["min_participants"]:
        fed["status"] = "ready"

    return {"federation_id": federation_id, "participant": participant}


@router.delete("/federations/{federation_id}/participants/{site_id}")
async def remove_participant(federation_id: str, site_id: str) -> dict[str, str]:
    """Remove a participant site from a federation."""
    if federation_id not in _federations:
        raise HTTPException(status_code=404, detail="Federation not found")

    fed = _federations[federation_id]
    original_len = len(fed["participants"])
    fed["participants"] = [p for p in fed["participants"] if p["id"] != site_id]

    if len(fed["participants"]) == original_len:
        raise HTTPException(status_code=404, detail=f"Participant {site_id} not found")

    return {"status": "removed", "site_id": site_id}


@router.post("/federations/{federation_id}/participants/{site_id}/reconnect")
async def reconnect_participant(federation_id: str, site_id: str) -> dict[str, str]:
    """Attempt to reconnect a disconnected participant."""
    if federation_id not in _federations:
        raise HTTPException(status_code=404, detail="Federation not found")

    fed = _federations[federation_id]
    for p in fed["participants"]:
        if p["id"] == site_id:
            if p.get("status") != "disconnected":
                raise HTTPException(
                    status_code=400,
                    detail=f"Participant {site_id} is not disconnected (status: {p.get('status')})",
                )
            p["status"] = "active"
            return {"status": "reconnected", "site_id": site_id}

    raise HTTPException(status_code=404, detail=f"Participant {site_id} not found")
