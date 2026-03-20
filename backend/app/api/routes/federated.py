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
