"""Memory management routes — conflicts, decay rules, network graph."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/memory", tags=["memory"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MemoryItem(BaseModel):
    id: str
    content: str
    category: str = "general"
    importance: float = Field(0.5, ge=0.0, le=1.0)
    created_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryConflict(BaseModel):
    id: str
    memory_a: MemoryItem
    memory_b: MemoryItem
    conflict_type: str = "contradiction"
    similarity: float = 0.0
    detected_at: float = Field(default_factory=time.time)


class ResolveRequest(BaseModel):
    action: str = Field(..., pattern=r"^(keep_a|keep_b|merge|ignore)$")
    merged_content: str | None = None


class DecayRule(BaseModel):
    id: str
    name: str
    category: str = "general"
    older_than_days: int = 30
    importance_below: float = Field(0.5, ge=0.0, le=1.0)
    reduce_by: int = Field(10, ge=1, le=100)
    every_n_days: int = Field(7, ge=1)
    min_floor: float = Field(0.1, ge=0.0, le=1.0)
    enabled: bool = True


class ApplyRulesRequest(BaseModel):
    rules: list[DecayRule] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# In-memory stub store
# ---------------------------------------------------------------------------

_conflicts: dict[str, dict[str, Any]] = {}
_conflict_counter = 0


def _seed_conflicts() -> None:
    """Seed sample conflicts for development."""
    global _conflict_counter
    if _conflicts:
        return

    samples: list[tuple[dict[str, Any], dict[str, Any], str, float]] = [
        (
            {
                "id": "mem-001",
                "content": "Camera feed #3 shows subject entering at 14:02",
                "category": "vision",
                "importance": 0.8,
                "created_at": time.time() - 86400,
                "metadata": {},
            },
            {
                "id": "mem-002",
                "content": "Camera feed #3 shows no activity between 14:00-14:15",
                "category": "vision",
                "importance": 0.7,
                "created_at": time.time() - 3600,
                "metadata": {},
            },
            "contradiction",
            0.82,
        ),
        (
            {
                "id": "mem-003",
                "content": "Audio analysis: gunshot detected at 200Hz peak",
                "category": "audio",
                "importance": 0.9,
                "created_at": time.time() - 7200,
                "metadata": {},
            },
            {
                "id": "mem-004",
                "content": "Audio analysis: car backfire at 200Hz peak",
                "category": "audio",
                "importance": 0.85,
                "created_at": time.time() - 3600,
                "metadata": {},
            },
            "ambiguity",
            0.91,
        ),
        (
            {
                "id": "mem-005",
                "content": "Pipeline result: 3 persons detected in frame",
                "category": "pipeline",
                "importance": 0.6,
                "created_at": time.time() - 1800,
                "metadata": {},
            },
            {
                "id": "mem-006",
                "content": "Pipeline result: 5 persons detected in same frame",
                "category": "pipeline",
                "importance": 0.65,
                "created_at": time.time() - 900,
                "metadata": {},
            },
            "duplicate",
            0.78,
        ),
    ]

    for mem_a, mem_b, ctype, sim in samples:
        _conflict_counter += 1
        cid = f"conflict-{_conflict_counter:04d}"
        _conflicts[cid] = {
            "id": cid,
            "memory_a": mem_a,
            "memory_b": mem_b,
            "conflict_type": ctype,
            "similarity": sim,
            "detected_at": time.time(),
        }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/conflicts")
async def get_conflicts() -> dict[str, Any]:
    """Return all unresolved memory conflicts."""
    _seed_conflicts()
    return {"conflicts": list(_conflicts.values()), "total": len(_conflicts)}


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    body: ResolveRequest,
) -> dict[str, Any]:
    """Resolve a memory conflict with the chosen action."""
    _seed_conflicts()
    if conflict_id not in _conflicts:
        raise HTTPException(status_code=404, detail="Conflict not found")

    conflict = _conflicts.pop(conflict_id)
    return {
        "resolved": True,
        "conflict_id": conflict_id,
        "action": body.action,
        "merged_content": body.merged_content,
        "remaining": len(_conflicts),
        "conflict": conflict,
    }


@router.post("/apply-rules")
async def apply_rules(body: ApplyRulesRequest) -> dict[str, Any]:
    """Apply decay rules to memories (stub — returns simulated result)."""
    enabled = [r for r in body.rules if r.enabled]
    # Simulate processing
    affected = sum(r.reduce_by for r in enabled)  # fake count
    return {
        "applied": len(enabled),
        "affected": min(affected, 50),
        "rules_received": len(body.rules),
        "message": f"Applied {len(enabled)} rule(s) successfully.",
    }
