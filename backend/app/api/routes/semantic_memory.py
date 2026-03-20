"""Semantic Memory API routes — store, recall, decay, promote, resolve, merge, export/import."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.memory.semantic_memory import SemanticMemoryService
from app.services.memory.promotion_rules import MemoryPromotionEngine
from app.services.memory.session_bridge import SessionBridge

router = APIRouter(prefix="/api/memory", tags=["semantic-memory"])

memory_service = SemanticMemoryService()
promotion_engine = MemoryPromotionEngine()
session_bridge = SessionBridge()

# Default workspace for demo/dev
DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class StoreRequest(BaseModel):
    content: str
    category: str = "fact"
    scope: str = "workspace"
    importance: float = 0.5
    source: str | None = None
    source_type: str = "system"
    confidence: float = 1.0
    tags: list[str] = Field(default_factory=list)
    owner_id: str | None = None
    is_private: bool = False
    ttl_days: int | None = None
    workspace_id: str | None = None


class RecallRequest(BaseModel):
    query: str
    scope: str | None = None
    category: str | None = None
    k: int = 10
    min_importance: float = 0.0
    include_private: bool = False
    owner_id: str | None = None
    workspace_id: str | None = None


class DecayRequest(BaseModel):
    decay_rate: float = 0.95
    workspace_id: str | None = None


class PromoteDemoteRequest(BaseModel):
    boost: float = 0.2


class ConflictRequest(BaseModel):
    memory_a_id: str
    memory_b_id: str


class MergeRequest(BaseModel):
    memory_ids: list[str]
    merged_content: str | None = None


class ImportRequest(BaseModel):
    memories: list[dict]
    workspace_id: str | None = None


class MemoryOut(BaseModel):
    id: str
    content: str
    category: str
    scope: str
    importance_score: float
    freshness_score: float
    access_count: int
    source: str | None
    source_type: str
    confidence: float
    is_private: bool
    tags: list[str]
    created_at: str | None

    class Config:
        from_attributes = True


def _to_out(m) -> dict:
    return {
        "id": str(m.id),
        "content": m.content,
        "category": m.category,
        "scope": str(m.scope) if m.scope else "workspace",
        "importance_score": m.importance_score,
        "freshness_score": m.freshness_score,
        "access_count": m.access_count,
        "source": m.source,
        "source_type": m.source_type,
        "confidence": m.confidence,
        "is_private": m.is_private,
        "tags": m.tags or [],
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _ws(body_ws_id: str | None) -> uuid.UUID:
    if body_ws_id:
        return uuid.UUID(body_ws_id)
    return DEFAULT_WORKSPACE_ID


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/store")
async def store_memory(body: StoreRequest, db: AsyncSession = Depends(get_db)):
    ws = _ws(body.workspace_id)
    owner = uuid.UUID(body.owner_id) if body.owner_id else None
    mem = await memory_service.store(
        db=db,
        workspace_id=ws,
        content=body.content,
        category=body.category,
        scope=body.scope,
        importance=body.importance,
        source=body.source,
        source_type=body.source_type,
        confidence=body.confidence,
        tags=body.tags,
        owner_id=owner,
        is_private=body.is_private,
        ttl_days=body.ttl_days,
    )
    await db.commit()
    return _to_out(mem)


@router.post("/recall")
async def recall_memories(body: RecallRequest, db: AsyncSession = Depends(get_db)):
    ws = _ws(body.workspace_id)
    owner = uuid.UUID(body.owner_id) if body.owner_id else None
    memories = await memory_service.recall(
        db=db,
        workspace_id=ws,
        query=body.query,
        scope=body.scope,
        category=body.category,
        k=body.k,
        min_importance=body.min_importance,
        include_private=body.include_private,
        owner_id=owner,
    )
    await db.commit()
    return [_to_out(m) for m in memories]


@router.post("/decay")
async def decay_memories(body: DecayRequest, db: AsyncSession = Depends(get_db)):
    ws = _ws(body.workspace_id)
    result = await memory_service.decay_all(db=db, workspace_id=ws, decay_rate=body.decay_rate)
    await db.commit()
    return result


@router.post("/promote/{memory_id}")
async def promote_memory(
    memory_id: str,
    body: PromoteDemoteRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    boost = body.boost if body else 0.2
    try:
        mem = await memory_service.promote(db=db, memory_id=uuid.UUID(memory_id), boost=boost)
        await db.commit()
        return _to_out(mem)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/demote/{memory_id}")
async def demote_memory(
    memory_id: str,
    body: PromoteDemoteRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    penalty = body.boost if body else 0.2
    try:
        mem = await memory_service.demote(db=db, memory_id=uuid.UUID(memory_id), penalty=penalty)
        await db.commit()
        return _to_out(mem)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/resolve-conflict")
async def resolve_conflict(body: ConflictRequest, db: AsyncSession = Depends(get_db)):
    try:
        mem = await memory_service.resolve_conflict(
            db=db,
            memory_id_a=uuid.UUID(body.memory_a_id),
            memory_id_b=uuid.UUID(body.memory_b_id),
        )
        await db.commit()
        return _to_out(mem)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/merge")
async def merge_memories(body: MergeRequest, db: AsyncSession = Depends(get_db)):
    ids = [uuid.UUID(mid) for mid in body.memory_ids]
    try:
        mem = await memory_service.merge_memories(
            db=db, memory_ids=ids, merged_content=body.merged_content
        )
        await db.commit()
        return _to_out(mem)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/summary")
async def memory_summary(
    workspace_id: str | None = Query(None),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    ws = _ws(workspace_id)
    return await memory_service.summarize(db=db, workspace_id=ws, category=category)


@router.get("/timeline")
async def memory_timeline(
    start: str = Query(..., description="ISO datetime start"),
    end: str = Query(..., description="ISO datetime end"),
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    ws = _ws(workspace_id)
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    memories = await memory_service.get_memory_timeline(
        db=db, workspace_id=ws, start=start_dt, end=end_dt
    )
    return [_to_out(m) for m in memories]


@router.post("/export")
async def export_memories(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    ws = _ws(workspace_id)
    return await memory_service.export_memories(db=db, workspace_id=ws)


@router.post("/import")
async def import_memories(body: ImportRequest, db: AsyncSession = Depends(get_db)):
    ws = _ws(body.workspace_id)
    result = await memory_service.import_memories(db=db, workspace_id=ws, memories=body.memories)
    await db.commit()
    return result


@router.post("/apply-rules")
async def apply_promotion_rules(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    ws = _ws(workspace_id)
    result = await promotion_engine.apply_rules(db=db, workspace_id=ws)
    await db.commit()
    return result
