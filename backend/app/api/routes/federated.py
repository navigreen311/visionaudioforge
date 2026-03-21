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
    site: str
    name: str
    data_size: int = 0
    status: str = "connected"


# ---------------------------------------------------------------------------
# Mock data — 3 pre-seeded federations
# ---------------------------------------------------------------------------

_mock_participants_1 = [
    {"site": "hospital-a", "name": "Hospital A", "data_size": 12000, "status": "connected", "joined_at": 1710000000.0},
    {"site": "hospital-b", "name": "Hospital B", "data_size": 8500, "status": "connected", "joined_at": 1710000100.0},
    {"site": "hospital-c", "name": "Hospital C", "data_size": 9200, "status": "connected", "joined_at": 1710000200.0},
]

_mock_participants_2 = [
    {"site": "site-east", "name": "East Campus", "data_size": 5000, "status": "connected", "joined_at": 1710001000.0},
    {"site": "site-west", "name": "West Campus", "data_size": 6300, "status": "connected", "joined_at": 1710001100.0},
]

_mock_participants_3 = [
    {"site": "node-1", "name": "Node 1", "data_size": 3200, "status": "disconnected", "joined_at": 1710002000.0},
    {"site": "node-2", "name": "Node 2", "data_size": 4100, "status": "connected", "joined_at": 1710002100.0},
    {"site": "node-3", "name": "Node 3", "data_size": 2800, "status": "connected", "joined_at": 1710002200.0},
    {"site": "node-4", "name": "Node 4", "data_size": 3600, "status": "connected", "joined_at": 1710002300.0},
]

_MOCK_IDS = ["fed-001", "fed-002", "fed-003"]

_federations: dict[str, dict] = {
    "fed-001": {
        "id": "fed-001",
        "name": "Medical Imaging Classifier",
        "model_id": "resnet50-chest-xray",
        "aggregation_strategy": "fedavg",
        "min_participants": 2,
        "total_rounds": 20,
        "current_round": 12,
        "status": "training",
        "participants": _mock_participants_1,
        "created_at": 1710000000.0,
        "privacy_budget": 8.0,
        "privacy_epsilon_spent": 3.4,
    },
    "fed-002": {
        "id": "fed-002",
        "name": "Audio Anomaly Detection",
        "model_id": "wav2vec-anomaly-v2",
        "aggregation_strategy": "fedprox",
        "min_participants": 2,
        "total_rounds": 15,
        "current_round": 15,
        "status": "completed",
        "participants": _mock_participants_2,
        "created_at": 1710001000.0,
        "privacy_budget": 10.0,
        "privacy_epsilon_spent": 9.8,
    },
    "fed-003": {
        "id": "fed-003",
        "name": "Cross-Modal Retrieval",
        "model_id": "clip-finetune-v1",
        "aggregation_strategy": "scaffold",
        "min_participants": 3,
        "total_rounds": 30,
        "current_round": 5,
        "status": "paused",
        "participants": _mock_participants_3,
        "created_at": 1710002000.0,
        "privacy_budget": 12.0,
        "privacy_epsilon_spent": 1.2,
    },
}


def _build_mock_rounds(federation_id: str, count: int = 12) -> list[dict]:
    """Generate mock round history for a federation."""
    fed = _federations.get(federation_id)
    num_participants = len(fed["participants"]) if fed else 3
    rounds = []
    for i in range(1, count + 1):
        rounds.append({
            "round": i,
            "status": "completed" if i < count else "in_progress",
            "accuracy": round(0.52 + i * 0.035, 4),
            "loss": round(1.8 - i * 0.12, 4),
            "privacy_epsilon_spent": round(i * 0.28, 4),
            "participants": num_participants,
            "started_at": 1710000000.0 + i * 3600,
            "completed_at": 1710000000.0 + i * 3600 + 1200 if i < count else None,
            "aggregation_time_ms": 450 + i * 30,
        })
    return rounds


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_federation(federation_id: str) -> dict:
    if federation_id not in _federations:
        raise HTTPException(status_code=404, detail="Federation not found")
    return _federations[federation_id]


# ---------------------------------------------------------------------------
# Endpoints — CRUD
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
        "privacy_budget": 10.0,
        "privacy_epsilon_spent": 0.0,
    }
    _federations[fid] = federation
    return federation


@router.get("/federations")
async def list_federations() -> list[dict]:
    """List all federations with status, round, and participant info."""
    return [
        {
            "id": f["id"],
            "name": f["name"],
            "model_id": f["model_id"],
            "aggregation_strategy": f["aggregation_strategy"],
            "status": f["status"],
            "current_round": f["current_round"],
            "total_rounds": f["total_rounds"],
            "participants": len(f["participants"]),
        }
        for f in _federations.values()
    ]


@router.get("/federations/{federation_id}")
async def get_federation(federation_id: str) -> dict:
    """Get full federation detail."""
    return _get_federation(federation_id)


# ---------------------------------------------------------------------------
# Endpoints — Join / Start Round (existing)
# ---------------------------------------------------------------------------

@router.post("/federations/{federation_id}/join")
async def join_federation(federation_id: str, body: JoinFederation) -> dict[str, Any]:
    """Join a federation as a participant."""
    fed = _get_federation(federation_id)
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
    fed = _get_federation(federation_id)
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
# Endpoints — Lifecycle (pause / resume / stop / export)
# ---------------------------------------------------------------------------

@router.post("/{federation_id}/pause")
async def pause_federation(federation_id: str) -> dict[str, str]:
    """Pause a running federation."""
    fed = _get_federation(federation_id)
    fed["status"] = "paused"
    return {"status": "paused"}


@router.post("/{federation_id}/resume")
async def resume_federation(federation_id: str) -> dict[str, str]:
    """Resume a paused federation."""
    fed = _get_federation(federation_id)
    fed["status"] = "training"
    return {"status": "training"}


@router.post("/{federation_id}/stop")
async def stop_federation(federation_id: str) -> dict[str, str]:
    """Stop a federation, marking it completed."""
    fed = _get_federation(federation_id)
    fed["status"] = "completed"
    return {"status": "completed"}


@router.post("/{federation_id}/export")
async def export_federation(federation_id: str) -> dict[str, Any]:
    """Export the aggregated model to the model registry."""
    fed = _get_federation(federation_id)
    return {
        "model_id": fed["model_id"],
        "exported_to_registry": True,
        "federation_id": federation_id,
        "rounds_completed": fed["current_round"],
    }


# ---------------------------------------------------------------------------
# Endpoints — Rounds
# ---------------------------------------------------------------------------

@router.get("/{federation_id}/rounds")
async def list_rounds(federation_id: str) -> list[dict]:
    """Return 12 mock training rounds with metrics."""
    _get_federation(federation_id)  # validate exists
    return _build_mock_rounds(federation_id, count=12)


# ---------------------------------------------------------------------------
# Endpoints — Participants
# ---------------------------------------------------------------------------

@router.post("/{federation_id}/participants")
async def add_participant(federation_id: str, body: AddParticipantRequest) -> dict[str, Any]:
    """Add a participant site to a federation."""
    fed = _get_federation(federation_id)
    participant = {
        "site": body.site,
        "name": body.name,
        "data_size": body.data_size,
        "status": body.status,
        "joined_at": time.time(),
    }
    fed["participants"].append(participant)
    if len(fed["participants"]) >= fed["min_participants"]:
        if fed["status"] == "waiting":
            fed["status"] = "ready"
    return {"federation_id": federation_id, "participant": participant}


@router.delete("/{federation_id}/participants/{site}")
async def remove_participant(federation_id: str, site: str) -> dict[str, Any]:
    """Remove a participant site from a federation."""
    fed = _get_federation(federation_id)
    original_len = len(fed["participants"])
    fed["participants"] = [
        p for p in fed["participants"] if p.get("site") != site
    ]
    if len(fed["participants"]) == original_len:
        raise HTTPException(status_code=404, detail=f"Participant '{site}' not found")
    return {"federation_id": federation_id, "removed": site, "remaining_participants": len(fed["participants"])}


@router.post("/{federation_id}/participants/{site}/reconnect")
async def reconnect_participant(federation_id: str, site: str) -> dict[str, str]:
    """Trigger reconnection for a disconnected participant."""
    fed = _get_federation(federation_id)
    for p in fed["participants"]:
        if p.get("site") == site:
            p["status"] = "reconnecting"
            return {"status": "reconnecting"}
    raise HTTPException(status_code=404, detail=f"Participant '{site}' not found")
