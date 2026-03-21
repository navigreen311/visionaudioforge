"""Memory API routes — store, search, delete, decay individual memories.

These endpoints power the Memory Explorer UI (ME1/ME2). They use an
in-memory store for now; swap in a real DB later.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/memory", tags=["memory"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class StoreMemoryRequest(BaseModel):
    content: str
    category: str = "fact"
    importance: int = Field(5, ge=1, le=10)
    scope: str = "workspace"
    is_private: bool = False
    source: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class MemoryResponse(BaseModel):
    id: str
    content: str
    category: str
    scope: str
    importance: int
    freshness_score: float
    access_count: int
    source: Optional[str]
    is_private: bool
    tags: list[str]
    created_at: Optional[str]
    last_accessed_at: Optional[str]
    decay_progress: float


# ---------------------------------------------------------------------------
# In-memory store (mock)
# ---------------------------------------------------------------------------

_memories: dict[str, dict[str, object]] = {}

# Seed some mock data on import
_SEED_DATA: list[dict[str, object]] = [
    {
        "content": "The primary model checkpoint is stored at s3://models/v2.3/checkpoint-final.pt and should not be overwritten without team approval.",
        "category": "fact",
        "importance": 9,
        "scope": "workspace",
        "tags": ["model", "s3", "checkpoint"],
        "source": "engineer-note",
    },
    {
        "content": "We decided to use FAISS IVF+PQ for the vector index because it balances speed and memory for 10M+ vectors.",
        "category": "decision",
        "importance": 8,
        "scope": "workspace",
        "tags": ["faiss", "vector-search", "architecture"],
        "source": "architecture-review",
    },
    {
        "content": "GPU utilization drops below 40% during data-loading phases of training. Consider prefetch workers.",
        "category": "observation",
        "importance": 6,
        "scope": "workspace",
        "tags": ["gpu", "training", "performance"],
        "source": "monitoring",
    },
    {
        "content": "API rate limit for OpenAI embeddings is 3000 RPM on the current plan. Batch requests accordingly.",
        "category": "alert",
        "importance": 7,
        "scope": "global",
        "tags": ["openai", "rate-limit", "embeddings"],
        "source": "ops-runbook",
    },
    {
        "content": "Team prefers Conventional Commits format for all repositories.",
        "category": "preference",
        "importance": 4,
        "scope": "global",
        "tags": ["git", "conventions"],
        "source": "team-standup",
    },
    {
        "content": "The staging environment uses a separate Postgres instance at staging-db.internal:5432.",
        "category": "context",
        "importance": 5,
        "scope": "workspace",
        "tags": ["staging", "database", "infra"],
        "source": "infra-doc",
    },
    {
        "content": "Audio augmentation pipeline must preserve sample rate at 16kHz for downstream ASR compatibility.",
        "category": "fact",
        "importance": 10,
        "scope": "workspace",
        "tags": ["audio", "augmentation", "asr"],
        "source": "tech-spec",
    },
    {
        "content": "User requested dark mode support for the dashboard — low priority for now.",
        "category": "preference",
        "importance": 2,
        "scope": "workspace",
        "tags": ["ui", "dark-mode"],
        "source": "user-feedback",
    },
]


def _seed() -> None:
    for i, seed in enumerate(_SEED_DATA):
        mid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        _memories[mid] = {
            "id": mid,
            "content": seed["content"],
            "category": seed["category"],
            "importance": seed["importance"],
            "scope": seed.get("scope", "workspace"),
            "is_private": False,
            "source": seed.get("source"),
            "tags": seed.get("tags", []),
            "freshness_score": round(1.0 - i * 0.08, 2),
            "access_count": max(0, 10 - i * 2),
            "created_at": now.isoformat(),
            "last_accessed_at": now.isoformat() if i < 5 else None,
            "decay_progress": round(i * 0.1, 2),
        }


_seed()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=MemoryResponse)
async def store_memory(body: StoreMemoryRequest) -> dict[str, object]:
    """Store a new memory entry."""
    mid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    memory: dict[str, object] = {
        "id": mid,
        "content": body.content,
        "category": body.category,
        "importance": body.importance,
        "scope": body.scope,
        "is_private": body.is_private,
        "source": body.source,
        "tags": body.tags,
        "freshness_score": 1.0,
        "access_count": 0,
        "created_at": now,
        "last_accessed_at": None,
        "decay_progress": 0.0,
    }
    _memories[mid] = memory
    return memory


@router.get("/search", response_model=list[MemoryResponse])
async def search_memories(
    q: str = Query("", description="Search query"),
    scope: str = Query("", description="Filter by scope"),
    category: str = Query("", description="Filter by category"),
    min_importance: int = Query(1, ge=1, le=10, description="Minimum importance"),
    include_private: bool = Query(False, description="Include private memories"),
) -> list[dict[str, object]]:
    """Search and filter memories."""
    results: list[dict[str, object]] = []
    for mem in _memories.values():
        if scope and mem["scope"] != scope:
            continue
        if category and mem["category"] != category:
            continue
        importance = mem["importance"]
        if isinstance(importance, (int, float)) and importance < min_importance:
            continue
        if not include_private and mem.get("is_private"):
            continue
        if q and q.lower() not in str(mem["content"]).lower():
            continue
        results.append(mem)

    results.sort(key=lambda m: (m.get("importance", 0),), reverse=True)
    return results


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str) -> dict[str, str]:
    """Delete a memory by ID."""
    if memory_id in _memories:
        del _memories[memory_id]
    return {"status": "deleted", "id": memory_id}


@router.post("/{memory_id}/decay")
async def decay_single_memory(memory_id: str) -> dict[str, object]:
    """Apply immediate decay to a single memory."""
    if memory_id not in _memories:
        return {"status": "not_found", "id": memory_id}
    mem = _memories[memory_id]
    current_decay = float(mem.get("decay_progress", 0))  # type: ignore[arg-type]
    mem["decay_progress"] = min(1.0, round(current_decay + 0.2, 2))
    current_freshness = float(mem.get("freshness_score", 1.0))  # type: ignore[arg-type]
    mem["freshness_score"] = max(0.0, round(current_freshness - 0.2, 2))
    return mem
