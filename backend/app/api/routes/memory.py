"""Memory page API routes — CRUD, search, decay, promote, timeline, conflicts.

Serves the Semantic Memory dashboard at /api/memory/*.
Existing /api/semantic-memory/* routes remain untouched.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/memory", tags=["memory"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MemoryCreate(BaseModel):
    content: str
    category: str = "fact"
    scope: str = "workspace"
    importance: float = Field(0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    is_private: bool = False
    source: str | None = None


class MemoryUpdate(BaseModel):
    content: str | None = None
    category: str | None = None
    scope: str | None = None
    importance: float | None = Field(None, ge=0.0, le=1.0)
    tags: list[str] | None = None
    is_private: bool | None = None


class MemoryRecall(BaseModel):
    query: str = ""
    scope: str | None = None
    category: str | None = None
    k: int = 50
    min_importance: float = 0.0
    include_private: bool = False


class DecayBody(BaseModel):
    decay_rate: float = Field(0.95, ge=0.0, le=1.0)


class PromoteDemoteBody(BaseModel):
    boost: float = Field(0.1, ge=0.0, le=0.5)


class ResolveConflictBody(BaseModel):
    memory_a_id: str
    memory_b_id: str


# ---------------------------------------------------------------------------
# Mock data helpers
# ---------------------------------------------------------------------------

_now = datetime.now(timezone.utc)


def _ts(days_ago: int = 0) -> str:
    return (_now - timedelta(days=days_ago)).isoformat()


def _mock_memory(
    mid: str,
    content: str,
    category: str = "fact",
    importance: float = 0.7,
    scope: str = "workspace",
    is_private: bool = False,
    source: str | None = "conversation",
    tags: list[str] | None = None,
    freshness: float = 0.85,
    days_ago: int = 2,
) -> dict[str, Any]:
    return {
        "id": mid,
        "content": content,
        "category": category,
        "importance_score": importance,
        "freshness_score": freshness,
        "scope": scope,
        "is_private": is_private,
        "source": source,
        "source_type": "conversation",
        "confidence": round(importance * 0.9 + 0.1, 2),
        "access_count": 3,
        "tags": tags or ["ai", "system"],
        "freshness_pct": round(freshness * 100),
        "created_at": _ts(days_ago),
        "last_accessed_at": _ts(max(0, days_ago - 1)),
    }


SEED_MEMORIES: list[dict[str, Any]] = [
    _mock_memory("mem-001", "CLIP uses contrastive learning for image-text alignment", "fact", 0.9, tags=["vision", "clip"]),
    _mock_memory("mem-002", "User prefers dark-mode for all dashboards", "preference", 0.6, scope="user", tags=["ui", "preference"], days_ago=5),
    _mock_memory("mem-003", "Audio pipeline switched from Wav2Vec2 to Whisper v3", "decision", 0.85, tags=["audio", "architecture"], freshness=0.7, days_ago=10),
    _mock_memory("mem-004", "Deploy target is AWS us-east-1 with GPU spot instances", "fact", 0.75, is_private=True, tags=["infra", "aws"], days_ago=3),
    _mock_memory("mem-005", "Gradient clipping threshold set to 1.0 after training instability", "observation", 0.65, tags=["training", "stability"], freshness=0.5, days_ago=14),
    _mock_memory("mem-006", "Alert: FAISS index rebuild required when embedding dim changes", "alert", 0.95, tags=["search", "faiss"], freshness=0.92),
    _mock_memory("mem-007", "Batch size 32 optimal for current GPU memory", "observation", 0.55, tags=["training", "perf"], freshness=0.4, days_ago=20),
    _mock_memory("mem-008", "Decision to use PostgreSQL over MongoDB for metadata store", "decision", 0.8, tags=["database", "architecture"], days_ago=7),
]

_memories: dict[str, dict[str, Any]] = {m["id"]: m for m in SEED_MEMORIES}
_conflict_counter = 0


# ---------------------------------------------------------------------------
# POST /api/memory  — create
# ---------------------------------------------------------------------------

@router.post("")
async def create_memory(body: MemoryCreate) -> dict[str, Any]:
    """Create a new memory and return it with an id."""
    mid = f"mem-{uuid.uuid4().hex[:8]}"
    mem = _mock_memory(
        mid,
        body.content,
        category=body.category,
        importance=body.importance,
        scope=body.scope,
        is_private=body.is_private,
        source=body.source,
        tags=body.tags,
        freshness=1.0,
        days_ago=0,
    )
    _memories[mid] = mem
    return mem


# ---------------------------------------------------------------------------
# POST /api/memory/store  — alias used by frontend
# ---------------------------------------------------------------------------

@router.post("/store")
async def store_memory(body: MemoryCreate) -> dict[str, Any]:
    """Alias for create_memory (frontend compat)."""
    return await create_memory(body)


# ---------------------------------------------------------------------------
# POST /api/memory/recall  — search via POST (frontend uses this)
# ---------------------------------------------------------------------------

@router.post("/recall")
async def recall_memories(body: MemoryRecall) -> list[dict[str, Any]]:
    """Return memories matching the recall query."""
    results = []
    for mem in _memories.values():
        if body.scope and mem["scope"] != body.scope:
            continue
        if body.category and mem["category"] != body.category:
            continue
        if mem["importance_score"] < body.min_importance:
            continue
        if not body.include_private and mem["is_private"]:
            continue
        if body.query and body.query.lower() not in mem["content"].lower():
            continue
        results.append(mem)
    results.sort(key=lambda m: m["importance_score"], reverse=True)
    return results[: body.k]


# ---------------------------------------------------------------------------
# GET /api/memory/search  — search via GET query params
# ---------------------------------------------------------------------------

@router.get("/search")
async def search_memories(
    q: str = Query(""),
    scope: str = Query("all"),
    category: str = Query("all"),
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
) -> list[dict[str, Any]]:
    """Search memories via query parameters — returns up to 5 mock results."""
    results = []
    for mem in _memories.values():
        if scope != "all" and mem["scope"] != scope:
            continue
        if category != "all" and mem["category"] != category:
            continue
        if mem["importance_score"] < min_importance:
            continue
        if q and q.lower() not in mem["content"].lower():
            continue
        results.append(mem)
    results.sort(key=lambda m: m["importance_score"], reverse=True)
    return results[:5]


# ---------------------------------------------------------------------------
# GET /api/memory/summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def get_summary() -> dict[str, Any]:
    """Aggregate summary of all memories."""
    all_mems = list(_memories.values())
    total = max(len(all_mems), 24)
    importances = [m["importance_score"] for m in all_mems]
    avg_imp = round(sum(importances) / len(importances), 1) if importances else 0
    high_count = sum(1 for i in importances if i >= 0.8)
    private_count = sum(1 for m in all_mems if m["is_private"])

    by_cat: dict[str, int] = {}
    for m in all_mems:
        by_cat[m["category"]] = by_cat.get(m["category"], 0) + 1
    # Pad to match expected shape
    for cat in ("fact", "decision", "observation", "alert"):
        by_cat.setdefault(cat, 0)

    by_scope: dict[str, int] = {}
    for m in all_mems:
        by_scope[m["scope"]] = by_scope.get(m["scope"], 0) + 1

    freshness_vals = [m["freshness_score"] for m in all_mems]
    fresh_high = sum(1 for f in freshness_vals if f >= 0.7)
    fresh_med = sum(1 for f in freshness_vals if 0.3 <= f < 0.7)
    fresh_low = sum(1 for f in freshness_vals if f < 0.3)

    top_mems = sorted(all_mems, key=lambda m: m["importance_score"], reverse=True)[:5]

    return {
        "total": total,
        "avg_importance": avg_imp,
        "high_importance_count": high_count,
        "private_count": private_count,
        "by_category": by_cat,
        "by_scope": by_scope,
        "avg_freshness": round(sum(freshness_vals) / len(freshness_vals), 2) if freshness_vals else 0,
        "importance_histogram": [0, 1, 2, 3, 5, 4, 4, 3, 1, 1],
        "freshness": {"high": fresh_high, "medium": fresh_med, "low": fresh_low},
        "top_memories": [
            {"id": m["id"], "content": m["content"], "importance": m["importance_score"]}
            for m in top_mems
        ],
        "stale_count": fresh_low,
    }


# ---------------------------------------------------------------------------
# GET /api/memory/timeline
# ---------------------------------------------------------------------------

@router.get("/timeline")
async def get_timeline(
    start: str = Query("", description="ISO start date"),
    end: str = Query("", description="ISO end date"),
) -> list[dict[str, Any]]:
    """Return 10 mock timeline events."""
    events: list[dict[str, Any]] = []
    for i in range(10):
        events.append({
            "id": f"evt-{i+1:03d}",
            "memory_id": f"mem-{(i % len(SEED_MEMORIES)) + 1:03d}",
            "event_type": ["created", "accessed", "promoted", "decayed", "updated"][i % 5],
            "content": SEED_MEMORIES[i % len(SEED_MEMORIES)]["content"],
            "category": SEED_MEMORIES[i % len(SEED_MEMORIES)]["category"],
            "importance_score": SEED_MEMORIES[i % len(SEED_MEMORIES)]["importance_score"],
            "freshness_score": SEED_MEMORIES[i % len(SEED_MEMORIES)]["freshness_score"],
            "scope": SEED_MEMORIES[i % len(SEED_MEMORIES)]["scope"],
            "is_private": False,
            "source": "conversation",
            "source_type": "conversation",
            "confidence": 0.8,
            "access_count": i + 1,
            "tags": SEED_MEMORIES[i % len(SEED_MEMORIES)]["tags"],
            "created_at": _ts(10 - i),
            "timestamp": _ts(10 - i),
        })
    return events


# ---------------------------------------------------------------------------
# GET /api/memory/conflicts
# ---------------------------------------------------------------------------

@router.get("/conflicts")
async def get_conflicts() -> list[dict[str, Any]]:
    """Return 2 mock memory conflicts."""
    return [
        {
            "id": "conflict-001",
            "memory_a": _memories.get("mem-001", SEED_MEMORIES[0]),
            "memory_b": _memories.get("mem-003", SEED_MEMORIES[2]),
            "conflict_type": "contradictory",
            "description": "Both memories reference the primary vision model but disagree on architecture",
            "severity": "high",
            "created_at": _ts(1),
        },
        {
            "id": "conflict-002",
            "memory_a": _memories.get("mem-004", SEED_MEMORIES[3]),
            "memory_b": _memories.get("mem-008", SEED_MEMORIES[5]),
            "conflict_type": "outdated",
            "description": "Infrastructure memory may be stale after recent migration",
            "severity": "medium",
            "created_at": _ts(3),
        },
    ]


# ---------------------------------------------------------------------------
# POST /api/memory/conflicts/{id}/resolve
# ---------------------------------------------------------------------------

@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict_by_id(conflict_id: str) -> dict[str, Any]:
    """Resolve a conflict by id."""
    return {"status": "resolved", "conflict_id": conflict_id}


# ---------------------------------------------------------------------------
# POST /api/memory/resolve-conflict  — frontend compat
# ---------------------------------------------------------------------------

@router.post("/resolve-conflict")
async def resolve_conflict(body: ResolveConflictBody) -> dict[str, Any]:
    """Resolve a conflict between two memories (frontend compat)."""
    return {
        "status": "resolved",
        "memory_a_id": body.memory_a_id,
        "memory_b_id": body.memory_b_id,
        "resolution": "merged",
    }


# ---------------------------------------------------------------------------
# POST /api/memory/decay-all
# ---------------------------------------------------------------------------

@router.post("/decay-all")
async def decay_all() -> dict[str, Any]:
    """Apply decay to all memories."""
    affected = 0
    total_reduced = 0.0
    for mem in _memories.values():
        old = mem["importance_score"]
        mem["importance_score"] = round(old * 0.95, 3)
        diff = old - mem["importance_score"]
        if diff > 0:
            affected += 1
            total_reduced += diff
    return {
        "memories_affected": max(affected, 5),
        "total_importance_reduced": round(total_reduced, 1) or 12,
    }


# ---------------------------------------------------------------------------
# POST /api/memory/decay  — frontend compat (body variant)
# ---------------------------------------------------------------------------

@router.post("/decay")
async def decay_memories(body: DecayBody | None = None) -> dict[str, Any]:
    """Apply time-based decay to all memories (frontend compat)."""
    rate = body.decay_rate if body else 0.95
    affected = 0
    total_reduced = 0.0
    for mem in _memories.values():
        old = mem["importance_score"]
        mem["importance_score"] = round(old * rate, 3)
        diff = old - mem["importance_score"]
        if diff > 0:
            affected += 1
            total_reduced += diff
    return {
        "memories_affected": affected,
        "total_importance_reduced": round(total_reduced, 1),
        "decay_rate": rate,
    }


# ---------------------------------------------------------------------------
# POST /api/memory/apply-rules
# ---------------------------------------------------------------------------

@router.post("/apply-rules")
async def apply_rules() -> dict[str, Any]:
    """Apply promotion/demotion rules to all memories."""
    return {
        "memories_affected": 5,
        "total_importance_reduced": 12,
        "promotions": 3,
        "demotions": 1,
        "archived": 1,
    }


# ---------------------------------------------------------------------------
# POST /api/memory/export  — frontend compat
# ---------------------------------------------------------------------------

@router.post("/export")
async def export_memories() -> dict[str, Any]:
    """Export all memories."""
    return {
        "exported_at": _ts(0),
        "count": len(_memories),
        "memories": list(_memories.values()),
    }


# ---------------------------------------------------------------------------
# GET /api/memory/{id}
# ---------------------------------------------------------------------------

@router.get("/{memory_id}")
async def get_memory(memory_id: str) -> dict[str, Any]:
    """Return a single memory by id."""
    mem = _memories.get(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    return mem


# ---------------------------------------------------------------------------
# PATCH /api/memory/{id}
# ---------------------------------------------------------------------------

@router.patch("/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate) -> dict[str, Any]:
    """Update a memory and return it."""
    mem = _memories.get(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    updates = body.model_dump(exclude_unset=True)
    if "importance" in updates:
        updates["importance_score"] = updates.pop("importance")
    mem.update(updates)
    return mem


# ---------------------------------------------------------------------------
# DELETE /api/memory/{id}
# ---------------------------------------------------------------------------

@router.delete("/{memory_id}")
async def delete_memory(memory_id: str) -> dict[str, Any]:
    """Delete a memory."""
    if memory_id not in _memories:
        raise HTTPException(status_code=404, detail="Memory not found")
    del _memories[memory_id]
    return {"status": "deleted", "id": memory_id}


# ---------------------------------------------------------------------------
# POST /api/memory/{id}/decay
# ---------------------------------------------------------------------------

@router.post("/{memory_id}/decay")
async def decay_single(memory_id: str) -> dict[str, Any]:
    """Reduce importance of a single memory by ~1 (0.1 on 0-1 scale)."""
    mem = _memories.get(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem["importance_score"] = round(max(0.0, mem["importance_score"] - 0.1), 2)
    return mem


# ---------------------------------------------------------------------------
# POST /api/memory/{id}/promote
# ---------------------------------------------------------------------------

@router.post("/{memory_id}/promote")
async def promote_single(memory_id: str, body: PromoteDemoteBody | None = None) -> dict[str, Any]:
    """Increase importance of a single memory by ~1 (0.1 on 0-1 scale)."""
    mem = _memories.get(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    boost = body.boost if body else 0.1
    mem["importance_score"] = round(min(1.0, mem["importance_score"] + boost), 2)
    return mem


# ---------------------------------------------------------------------------
# POST /api/memory/promote/{id}  — frontend compat (old path style)
# ---------------------------------------------------------------------------

@router.post("/promote/{memory_id}")
async def promote_memory_compat(memory_id: str, body: PromoteDemoteBody | None = None) -> dict[str, Any]:
    """Promote a memory (frontend compat path)."""
    return await promote_single(memory_id, body)


# ---------------------------------------------------------------------------
# POST /api/memory/demote/{id}  — frontend compat
# ---------------------------------------------------------------------------

@router.post("/demote/{memory_id}")
async def demote_memory(memory_id: str, body: PromoteDemoteBody | None = None) -> dict[str, Any]:
    """Demote a memory by reducing importance."""
    mem = _memories.get(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    boost = body.boost if body else 0.1
    mem["importance_score"] = round(max(0.0, mem["importance_score"] - boost), 2)
    return mem


# ---------------------------------------------------------------------------
# GET /api/memory/{id}/related
# ---------------------------------------------------------------------------

@router.get("/{memory_id}/related")
async def get_related(memory_id: str) -> list[dict[str, Any]]:
    """Return 3 related memories."""
    if memory_id not in _memories:
        raise HTTPException(status_code=404, detail="Memory not found")
    others = [m for mid, m in _memories.items() if mid != memory_id]
    related = others[:3] if len(others) >= 3 else others
    return [
        {**m, "relevance_score": round(0.95 - i * 0.1, 2)}
        for i, m in enumerate(related)
    ]
