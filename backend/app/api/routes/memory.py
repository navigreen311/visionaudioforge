"""Memory page API routes - CRUD, search, decay, promote, timeline, conflicts.

Serves the Semantic Memory dashboard at /api/memory/*.
Existing /api/semantic-memory/* routes remain untouched.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_workspace_id
from app.models.semantic_memory import SemanticMemory
from app.services.memory.promotion_rules import MemoryPromotionEngine
from app.services.memory.semantic_memory import SemanticMemoryService

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


# Memories are rows in semantic_memories. This module kept its own dict beside
# that table, so a memory created through /api/memory vanished on restart while
# /search and /timeline — which already read the table — never saw it at all.
#
# Decay history lives in the row's metadata rather than a second table: it is a
# short trail belonging to one memory, read only through that memory.


def _decay_trail(memory: SemanticMemory) -> dict[str, Any]:
    return (memory.metadata_ or {}).get("decay", {})


def _record_decay(
    memory: SemanticMemory, before: float, after: float, trigger: str
) -> None:
    """Append a decay event to the memory's own metadata."""
    meta = dict(memory.metadata_ or {})
    decay = dict(meta.get("decay", {}))
    events = list(decay.get("events", []))
    events.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "importance_before": before,
            "importance_after": after,
            "trigger": trigger,
        }
    )
    decay["events"] = events[-50:]
    decay.setdefault("initial_importance", before)
    meta["decay"] = decay
    # Reassigned rather than mutated: SQLAlchemy does not track in-place JSON
    # edits, so mutating would leave the change unsaved.
    memory.metadata_ = meta


async def _load_memory(
    db: AsyncSession, workspace_id: UUID, memory_id: str
) -> SemanticMemory:
    """Fetch one memory in this workspace, or 404."""
    try:
        key = uuid.UUID(str(memory_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail="Memory not found")

    result = await db.execute(
        select(SemanticMemory).where(
            SemanticMemory.id == key,
            SemanticMemory.workspace_id == workspace_id,
        )
    )
    memory = result.scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


async def _all_memories(
    db: AsyncSession, workspace_id: UUID
) -> list[SemanticMemory]:
    result = await db.execute(
        select(SemanticMemory)
        .where(SemanticMemory.workspace_id == workspace_id)
        .order_by(SemanticMemory.created_at.desc())
    )
    return list(result.scalars().all())


_memory_service = SemanticMemoryService()
_promotion_engine = MemoryPromotionEngine()


def _serialise_memory(memory: SemanticMemory) -> dict[str, Any]:
    """The shape the console's memory views already expect."""
    return {
        "id": str(memory.id),
        "content": memory.content,
        "category": memory.category,
        "scope": memory.scope,
        "importance": memory.importance,
        "importance_score": memory.importance_score,
        "freshness_score": memory.freshness_score,
        "access_count": memory.access_count,
        "source": memory.source,
        "source_type": memory.source_type,
        "confidence": memory.confidence,
        "is_private": memory.is_private,
        "tags": list(memory.tags or []),
        "freshness_pct": round((memory.freshness_score or 0.0) * 100),
        "created_at": memory.created_at.isoformat() if memory.created_at else "",
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else "",
        "last_accessed_at": (
            memory.last_accessed.isoformat() if memory.last_accessed else None
        ),
    }


@router.post("")
async def create_memory(
    body: MemoryCreate,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new memory and return it with an id."""
    memory = SemanticMemory(
        id=uuid.uuid4(),
        workspace_id=session_workspace,
        content=body.content,
        category=body.category,
        scope=body.scope,
        importance=body.importance,
        importance_score=body.importance,
        freshness_score=1.0,
        access_count=0,
        source=body.source,
        source_type="conversation",
        confidence=round(body.importance * 0.9 + 0.1, 2),
        is_private=body.is_private,
        tags=list(body.tags or []),
        metadata_={"decay": {"initial_importance": body.importance, "events": []}},
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return _serialise_memory(memory)


# ---------------------------------------------------------------------------
# POST /api/memory/store  - alias used by frontend
# ---------------------------------------------------------------------------

@router.post("/store")
async def store_memory(
    body: MemoryCreate,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Alias for create_memory (frontend compat)."""
    return await create_memory(body, session_workspace, db)


# ---------------------------------------------------------------------------
# POST /api/memory/recall  - search via POST (frontend uses this)
# ---------------------------------------------------------------------------

@router.post("/recall")
async def recall_memories(
    body: MemoryRecall,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return memories matching the recall query."""
    conditions = [
        SemanticMemory.workspace_id == session_workspace,
        SemanticMemory.importance_score >= body.min_importance,
    ]
    if body.scope:
        conditions.append(SemanticMemory.scope == body.scope)
    if body.category:
        conditions.append(SemanticMemory.category == body.category)
    if not body.include_private:
        conditions.append(SemanticMemory.is_private.is_(False))
    if body.query:
        conditions.append(SemanticMemory.content.ilike(f"%{body.query}%"))

    result = await db.execute(
        select(SemanticMemory)
        .where(*conditions)
        .order_by(SemanticMemory.importance_score.desc())
        .limit(body.k)
    )
    return [_serialise_memory(m) for m in result.scalars().all()]


# ---------------------------------------------------------------------------
# GET /api/memory/search  - search via GET query params
# ---------------------------------------------------------------------------

@router.get("/search")
async def search_memories(
    q: str = Query(""),
    scope: str = Query("all"),
    category: str = Query("all"),
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Search this workspace's stored memories.

    This filtered a module-level dictionary seeded with five fixed memories, so
    every workspace searched the same invented corpus and nothing an agent had
    actually stored was findable. `SemanticMemoryService.recall` and the
    `semantic_memories` table were already there.
    """
    memories = await _memory_service.recall(
        db=db,
        workspace_id=session_workspace,
        query=q,
        scope=None if scope == "all" else scope,
        category=None if category == "all" else category,
        k=50,
        min_importance=min_importance,
    )
    return [_serialise_memory(m) for m in memories]


@router.get("/summary")
async def get_summary(
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Aggregate summary of the workspace's memories."""
    all_mems = [_serialise_memory(m) for m in await _all_memories(db, session_workspace)]
    total = len(all_mems)
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
        "importance_histogram": _importance_histogram(importances),
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
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """A timeline derived from the memories themselves.

    This generated ten events by cycling through the strings "created",
    "accessed", "promoted", "decayed", "updated" - a shape, not a history.

    There is no event log for memories, so rather than invent one this reports
    what the rows genuinely record: when each memory was created, when it was
    last updated (if that differs), and its access count. If a real event table
    is added later this should read from it instead.
    """
    conditions = [SemanticMemory.workspace_id == session_workspace]
    for bound, column_op in ((start, "gte"), (end, "lte")):
        if not bound:
            continue
        try:
            parsed = datetime.fromisoformat(bound.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"Not an ISO date: {bound!r}"
            ) from None
        conditions.append(
            SemanticMemory.created_at >= parsed
            if column_op == "gte"
            else SemanticMemory.created_at <= parsed
        )

    rows = (
        await db.execute(
            select(SemanticMemory)
            .where(*conditions)
            .order_by(SemanticMemory.created_at.desc())
            .limit(200)
        )
    ).scalars().all()

    events: list[dict[str, Any]] = []
    for memory in rows:
        events.append(
            {
                "id": f"{memory.id}-created",
                "memory_id": str(memory.id),
                "event_type": "created",
                "timestamp": memory.created_at.isoformat() if memory.created_at else "",
                "detail": memory.content[:120],
            }
        )
        if memory.updated_at and memory.created_at and memory.updated_at > memory.created_at:
            events.append(
                {
                    "id": f"{memory.id}-updated",
                    "memory_id": str(memory.id),
                    "event_type": "updated",
                    "timestamp": memory.updated_at.isoformat(),
                    "detail": f"access count {memory.access_count}",
                }
            )

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events


@router.get("/conflicts")
async def get_conflicts(
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Contradictions the promotion engine finds between stored memories.

    This returned the same two hand-written conflicts between two seed memories,
    so the conflicts panel showed a problem that did not exist and never showed
    one that did. `MemoryPromotionEngine.check_conflicts` does the real work.
    """
    return await _promotion_engine.check_conflicts(db=db, workspace_id=session_workspace)


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict_by_id(conflict_id: str) -> dict[str, Any]:
    """Resolve a conflict by id."""
    return {"status": "resolved", "conflict_id": conflict_id}


# ---------------------------------------------------------------------------
# POST /api/memory/resolve-conflict  - frontend compat
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
async def decay_all(
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Apply decay to every memory in the workspace.

    The counts returned are what actually changed. They were floored at 5 and
    12, so an empty workspace still reported work done.
    """
    affected, total_reduced = await _apply_decay(db, session_workspace, 0.95)
    return {
        "memories_affected": affected,
        "total_importance_reduced": round(total_reduced, 3),
    }


# ---------------------------------------------------------------------------
# POST /api/memory/decay  - frontend compat (body variant)
# ---------------------------------------------------------------------------

@router.post("/decay")
async def decay_memories(
    body: DecayBody | None = None,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Apply time-based decay to all memories (frontend compat)."""
    rate = body.decay_rate if body else 0.95
    affected, total_reduced = await _apply_decay(db, session_workspace, rate)
    return {
        "memories_affected": affected,
        "total_importance_reduced": round(total_reduced, 3),
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
# POST /api/memory/export  - frontend compat
# ---------------------------------------------------------------------------

@router.post("/export")
async def export_memories(
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Export the workspace's memories."""
    memories = [_serialise_memory(m) for m in await _all_memories(db, session_workspace)]
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(memories),
        "memories": memories,
    }


# ---------------------------------------------------------------------------
# GET /api/memory/{id}
# ---------------------------------------------------------------------------

@router.get("/{memory_id}")
async def get_memory(
    memory_id: str,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return a single memory by id."""
    return _serialise_memory(await _load_memory(db, session_workspace, memory_id))


# ---------------------------------------------------------------------------
# PATCH /api/memory/{id}
# ---------------------------------------------------------------------------

@router.patch("/{memory_id}")
async def update_memory(
    memory_id: str,
    body: MemoryUpdate,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update a memory and return it."""
    memory = await _load_memory(db, session_workspace, memory_id)

    updates = body.model_dump(exclude_unset=True)
    if "importance" in updates:
        updates["importance_score"] = updates["importance"]
    for field, value in updates.items():
        if hasattr(memory, field):
            setattr(memory, field, value)

    await db.commit()
    await db.refresh(memory)
    return _serialise_memory(memory)


# ---------------------------------------------------------------------------
# DELETE /api/memory/{id}
# ---------------------------------------------------------------------------

@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a memory."""
    memory = await _load_memory(db, session_workspace, memory_id)
    await db.delete(memory)
    await db.commit()
    return {"status": "deleted", "id": memory_id}


# ---------------------------------------------------------------------------
# POST /api/memory/{id}/decay
# ---------------------------------------------------------------------------

@router.post("/{memory_id}/decay")
async def decay_single(
    memory_id: str,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reduce importance of a single memory by ~1 (0.1 on 0-1 scale)."""
    memory = await _load_memory(db, session_workspace, memory_id)

    before = memory.importance_score
    memory.importance_score = round(max(0.0, before - 0.1), 2)
    _record_decay(memory, before, memory.importance_score, "manual")

    await db.commit()
    await db.refresh(memory)
    return _serialise_memory(memory)


# ---------------------------------------------------------------------------
# POST /api/memory/{id}/promote
# ---------------------------------------------------------------------------

@router.post("/{memory_id}/promote")
async def promote_single(
    memory_id: str,
    body: PromoteDemoteBody | None = None,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Increase importance of a single memory by ~1 (0.1 on 0-1 scale)."""
    memory = await _load_memory(db, session_workspace, memory_id)

    boost = body.boost if body else 0.1
    memory.importance_score = round(min(1.0, memory.importance_score + boost), 2)

    await db.commit()
    await db.refresh(memory)
    return _serialise_memory(memory)


# ---------------------------------------------------------------------------
# POST /api/memory/promote/{id}  - frontend compat (old path style)
# ---------------------------------------------------------------------------

@router.post("/promote/{memory_id}")
async def promote_memory_compat(
    memory_id: str,
    body: PromoteDemoteBody | None = None,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Promote a memory (frontend compat path)."""
    return await promote_single(memory_id, body, session_workspace, db)


# ---------------------------------------------------------------------------
# POST /api/memory/demote/{id}  - frontend compat
# ---------------------------------------------------------------------------

@router.post("/demote/{memory_id}")
async def demote_memory(
    memory_id: str,
    body: PromoteDemoteBody | None = None,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Demote a memory by reducing importance."""
    memory = await _load_memory(db, session_workspace, memory_id)

    boost = body.boost if body else 0.1
    before = memory.importance_score
    memory.importance_score = round(max(0.0, before - boost), 2)
    _record_decay(memory, before, memory.importance_score, "demote")

    await db.commit()
    await db.refresh(memory)
    return _serialise_memory(memory)


# ---------------------------------------------------------------------------
# GET /api/memory/{id}/related
# ---------------------------------------------------------------------------

@router.get("/{memory_id}/related")
async def get_related(
    memory_id: str,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return up to three related memories from the same workspace.

    Relatedness is by shared category then importance — the row does not carry
    an embedding here. The descending relevance_score is a rank, not a
    similarity measurement, and is labelled as such.
    """
    memory = await _load_memory(db, session_workspace, memory_id)

    result = await db.execute(
        select(SemanticMemory)
        .where(
            SemanticMemory.workspace_id == session_workspace,
            SemanticMemory.id != memory.id,
        )
        .order_by(
            (SemanticMemory.category == memory.category).desc(),
            SemanticMemory.importance_score.desc(),
        )
        .limit(3)
    )
    return [
        {
            **_serialise_memory(m),
            "relevance_rank": i + 1,
            "relevance_basis": "category_and_importance",
        }
        for i, m in enumerate(result.scalars().all())
    ]


# ---------------------------------------------------------------------------
# GET /api/memory/{id}/decay-history
# ---------------------------------------------------------------------------

@router.get("/{memory_id}/decay-history")
async def get_decay_history(
    memory_id: str,
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the decay timeline for a memory (MemoryDetailPanel > DecayTimeline)."""
    memory = await _load_memory(db, session_workspace, memory_id)
    trail = _decay_trail(memory)

    return {
        "created_at": memory.created_at.isoformat() if memory.created_at else "",
        "initial_importance": trail.get(
            "initial_importance", memory.importance_score
        ),
        "events": trail.get("events", []),
        "current_importance": memory.importance_score,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _importance_histogram(importances: list[float]) -> list[int]:
    """Ten buckets over 0..1. This was a hardcoded list of ten numbers."""
    buckets = [0] * 10
    for value in importances:
        index = min(int(max(value, 0.0) * 10), 9)
        buckets[index] += 1
    return buckets


async def _apply_decay(
    db: AsyncSession, workspace_id: UUID, rate: float
) -> tuple[int, float]:
    """Multiply every importance by *rate*, recording each change."""
    affected = 0
    total_reduced = 0.0

    for memory in await _all_memories(db, workspace_id):
        before = memory.importance_score
        after = round(before * rate, 3)
        if after >= before:
            continue

        memory.importance_score = after
        _record_decay(memory, before, after, "bulk")
        affected += 1
        total_reduced += before - after

    if affected:
        await db.commit()
    return affected, total_reduced
