"""Semantic Memory routes — store, recall, decay, promote memories."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/semantic-memory", tags=["semantic-memory"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MemoryStore(BaseModel):
    content: str
    category: str = "general"
    importance: float = Field(0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str | None = None


class MemoryRecallRequest(BaseModel):
    query: str
    limit: int = 10
    category: str | None = None


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_memories: dict[str, dict] = {}
_mem_counter = 0


def _next_id() -> str:
    global _mem_counter
    _mem_counter += 1
    return f"mem-{_mem_counter:06d}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/store")
async def store_memory(body: MemoryStore) -> dict[str, Any]:
    """Store a new semantic memory."""
    mid = _next_id()
    memory = {
        "id": mid,
        "content": body.content,
        "category": body.category,
        "importance": body.importance,
        "metadata": body.metadata,
        "created_at": time.time(),
        "access_count": 0,
    }
    _memories[mid] = memory
    return memory


@router.post("/recall")
async def recall_memory(body: MemoryRecallRequest) -> dict[str, Any]:
    """Recall memories matching a query."""
    results = []
    for mem in _memories.values():
        if body.category and mem["category"] != body.category:
            continue
        # Simple keyword match (production uses embeddings)
        if body.query.lower() in mem["content"].lower():
            mem["access_count"] += 1
            results.append(mem)
    results.sort(key=lambda m: m["importance"], reverse=True)
    return {"query": body.query, "results": results[: body.limit], "total": len(results)}


@router.post("/decay")
async def decay_memories(
    threshold: float = Query(0.1, ge=0.0, le=1.0),
    factor: float = Query(0.9, ge=0.0, le=1.0),
) -> dict[str, Any]:
    """Apply time-based decay to all memories below a threshold."""
    decayed = 0
    for mem in _memories.values():
        if mem["importance"] < threshold:
            continue
        mem["importance"] *= factor
        decayed += 1
    return {"decayed_count": decayed, "factor": factor}


@router.post("/promote/{memory_id}")
async def promote_memory(memory_id: str, boost: float = Query(0.1, ge=0.0, le=0.5)) -> dict[str, Any]:
    """Promote a memory by boosting its importance."""
    if memory_id not in _memories:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem = _memories[memory_id]
    mem["importance"] = min(1.0, mem["importance"] + boost)
    return mem


@router.get("/memories")
async def list_memories(limit: int = Query(50, ge=1, le=500)) -> list[dict]:
    """List all stored memories."""
    return sorted(_memories.values(), key=lambda m: m["importance"], reverse=True)[:limit]
