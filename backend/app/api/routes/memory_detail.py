"""Memory detail routes — CRUD, decay, promote, related for individual memories.

These endpoints power the MemoryDetailPanel slide-over in the frontend.
Uses an in-memory store stub; swap with DB queries in production.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/memory", tags=["memory-detail"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MemoryPatch(BaseModel):
    """Partial update payload for a memory."""
    content: str | None = None
    category: str | None = None
    importance: float | None = Field(None, ge=0.0, le=1.0)
    scope: str | None = None
    is_private: bool | None = None
    source: str | None = None
    tags: list[str] | None = None
    archived: bool | None = None


class RelatedMemoryOut(BaseModel):
    id: str
    content: str
    similarity: float
    category: str


class DecayEventOut(BaseModel):
    timestamp: str
    importance_before: float
    importance_after: float
    trigger: str


class DecayHistoryOut(BaseModel):
    created_at: str
    initial_importance: float
    events: list[DecayEventOut]
    current_importance: float


# ---------------------------------------------------------------------------
# In-memory stub store (mirrors semantic_memory store for demo purposes)
# ---------------------------------------------------------------------------

_memories: dict[str, dict[str, Any]] = {}
_decay_events: dict[str, list[dict[str, Any]]] = {}
_initial_importance: dict[str, float] = {}
_counter = 0


def _seed_if_empty() -> None:
    """Seed some demo data so the panel has something to show."""
    global _counter
    if _memories:
        return
    now = datetime.now(timezone.utc).isoformat()
    samples = [
        {"content": "User prefers dark mode across all workspaces.", "category": "preference", "importance": 0.8},
        {"content": "API rate limit is 1000 req/min per workspace.", "category": "fact", "importance": 0.9},
        {"content": "Weekly model retraining happens on Sundays at 02:00 UTC.", "category": "procedure", "importance": 0.7},
    ]
    for s in samples:
        _counter += 1
        mid = f"mem-{_counter:06d}"
        _memories[mid] = {
            "id": mid,
            "content": s["content"],
            "category": s["category"],
            "importance": s["importance"],
            "importance_score": s["importance"],
            "freshness_score": 1.0,
            "scope": "workspace",
            "is_private": False,
            "source": "system",
            "source_type": "system",
            "tags": [],
            "access_count": 0,
            "confidence": 1.0,
            "created_at": now,
            "updated_at": now,
            "last_accessed": None,
            "archived": False,
            "metadata": {},
        }
        _initial_importance[mid] = s["importance"]
        _decay_events[mid] = []


def _get_or_404(memory_id: str) -> dict[str, Any]:
    _seed_if_empty()
    if memory_id not in _memories:
        raise HTTPException(status_code=404, detail="Memory not found")
    return _memories[memory_id]


# ---------------------------------------------------------------------------
# GET /api/memory/{id}
# ---------------------------------------------------------------------------

@router.get("/{memory_id}")
async def get_memory(memory_id: str) -> dict[str, Any]:
    """Return a single memory by ID."""
    mem = _get_or_404(memory_id)
    mem["access_count"] += 1
    mem["last_accessed"] = datetime.now(timezone.utc).isoformat()
    return mem


# ---------------------------------------------------------------------------
# PATCH /api/memory/{id}  (auto-save from panel)
# ---------------------------------------------------------------------------

@router.patch("/{memory_id}")
async def patch_memory(memory_id: str, body: MemoryPatch) -> dict[str, Any]:
    """Partially update a memory (content, metadata fields, archive flag)."""
    mem = _get_or_404(memory_id)
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        mem[key] = value
    mem["updated_at"] = datetime.now(timezone.utc).isoformat()
    return mem


# ---------------------------------------------------------------------------
# DELETE /api/memory/{id}
# ---------------------------------------------------------------------------

@router.delete("/{memory_id}")
async def delete_memory(memory_id: str) -> dict[str, str]:
    """Delete a memory permanently."""
    _get_or_404(memory_id)
    del _memories[memory_id]
    _decay_events.pop(memory_id, None)
    _initial_importance.pop(memory_id, None)
    return {"status": "deleted", "id": memory_id}


# ---------------------------------------------------------------------------
# POST /api/memory/{id}/decay
# ---------------------------------------------------------------------------

@router.post("/{memory_id}/decay")
async def decay_single_memory(
    memory_id: str,
    factor: float = 0.9,
) -> dict[str, Any]:
    """Apply decay to a single memory."""
    mem = _get_or_404(memory_id)
    before = mem["importance"]
    mem["importance"] = round(before * factor, 4)
    mem["updated_at"] = datetime.now(timezone.utc).isoformat()

    _decay_events.setdefault(memory_id, []).append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "importance_before": before,
        "importance_after": mem["importance"],
        "trigger": "manual_decay",
    })
    return mem


# ---------------------------------------------------------------------------
# POST /api/memory/{id}/promote
# ---------------------------------------------------------------------------

@router.post("/{memory_id}/promote")
async def promote_single_memory(
    memory_id: str,
    boost: float = 0.1,
) -> dict[str, Any]:
    """Promote a memory by boosting its importance score."""
    mem = _get_or_404(memory_id)
    before = mem["importance"]
    mem["importance"] = min(1.0, round(before + boost, 4))
    mem["updated_at"] = datetime.now(timezone.utc).isoformat()

    _decay_events.setdefault(memory_id, []).append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "importance_before": before,
        "importance_after": mem["importance"],
        "trigger": "manual_promote",
    })
    return mem


# ---------------------------------------------------------------------------
# GET /api/memory/{id}/related
# ---------------------------------------------------------------------------

@router.get("/{memory_id}/related")
async def get_related_memories(memory_id: str) -> dict[str, Any]:
    """Return top-3 related memories (stub: returns other memories with fake similarity)."""
    _get_or_404(memory_id)
    _seed_if_empty()

    related: list[dict[str, Any]] = []
    for mid, mem in _memories.items():
        if mid == memory_id:
            continue
        related.append({
            "id": mid,
            "content": mem["content"],
            "similarity": round(0.65 + (hash(mid) % 30) / 100, 2),
            "category": mem["category"],
        })
    # Sort by fake similarity desc, take top 3
    related.sort(key=lambda r: r["similarity"], reverse=True)
    return {"related": related[:3]}


# ---------------------------------------------------------------------------
# GET /api/memory/{id}/decay-history
# ---------------------------------------------------------------------------

@router.get("/{memory_id}/decay-history")
async def get_decay_history(memory_id: str) -> DecayHistoryOut:
    """Return the decay history timeline for a memory."""
    mem = _get_or_404(memory_id)
    events = _decay_events.get(memory_id, [])
    return DecayHistoryOut(
        created_at=mem["created_at"],
        initial_importance=_initial_importance.get(memory_id, mem["importance"]),
        events=[DecayEventOut(**e) for e in events],
        current_importance=mem["importance"],
    )
