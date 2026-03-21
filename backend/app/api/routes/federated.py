"""Federated Learning routes — federation management, rounds, aggregation."""

from __future__ import annotations

import math
import random
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


# ---------------------------------------------------------------------------
# Round history with mock data (FL4 / FL5 charts)
# ---------------------------------------------------------------------------

class RoundDataResponse(BaseModel):
    round_number: int
    accuracy: float | None
    loss: float | None
    privacy_epsilon_spent: float
    participants: int
    duration_s: float | None


def _generate_mock_rounds(seed: str, count: int = 12) -> list[dict[str, Any]]:
    """Generate deterministic mock round data for a given federation id."""
    rng = random.Random(seed)
    rounds: list[dict[str, Any]] = []
    for i in range(1, count + 1):
        # Accuracy climbs from ~55% towards ~93% with noise
        base_acc = 55 + 38 * (1 - math.exp(-0.25 * i))
        accuracy = round(min(base_acc + rng.gauss(0, 2.5), 99.5), 2)

        # Loss drops from ~1.8 towards ~0.15
        base_loss = 1.8 * math.exp(-0.3 * i) + 0.12
        loss = round(max(base_loss + rng.gauss(0, 0.05), 0.01), 4)

        # Privacy epsilon per round: small value with slight variance
        epsilon = round(0.4 + rng.uniform(-0.08, 0.12), 4)

        participants = rng.choice([3, 4, 5])
        duration = round(rng.uniform(8.0, 35.0), 1)

        rounds.append({
            "round_number": i,
            "accuracy": accuracy,
            "loss": loss,
            "privacy_epsilon_spent": epsilon,
            "participants": participants,
            "duration_s": duration,
        })
    return rounds


@router.get("/federations/{federation_id}/rounds")
async def get_federation_rounds(federation_id: str) -> list[dict[str, Any]]:
    """Return per-round training metrics (mock data for now).

    Provides 12 rounds of accuracy, loss, and differential-privacy
    epsilon spend for the FL4 (Accuracy/Loss) and FL5 (Privacy Budget)
    charts.
    """
    # Return deterministic mock data keyed by federation_id so the same
    # id always returns the same series.
    return _generate_mock_rounds(seed=federation_id)
