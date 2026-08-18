"""Semantic Memory routes — store, recall, decay, promote memories.

Memories are rows in ``semantic_memories``. They used to be a module-level
dict: user-authored knowledge that the platform promised to remember and then
lost on every restart, with nothing to indicate anything had been forgotten.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.semantic_memory import SemanticMemory

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
    workspace_id: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialise(memory: SemanticMemory) -> dict[str, Any]:
    return {
        "id": str(memory.id),
        "content": memory.content,
        "category": memory.category,
        "importance": memory.importance,
        "metadata": memory.metadata_ or {},
        "created_at": memory.created_at.timestamp() if memory.created_at else None,
        "access_count": memory.access_count,
        "workspace_id": str(memory.workspace_id) if memory.workspace_id else None,
    }


def _require_workspace(workspace_id: str | None) -> uuid.UUID:
    """Memories are workspace-scoped; refuse to store one without a workspace."""
    if not workspace_id:
        raise HTTPException(
            status_code=422,
            detail="workspace_id is required — memories are workspace-scoped",
        )
    try:
        return uuid.UUID(str(workspace_id))
    except ValueError:
        raise HTTPException(status_code=422, detail="workspace_id must be a UUID")


def _scoped(stmt, workspace_id: str | None):
    """Constrain a query to one workspace when one was supplied."""
    if workspace_id:
        return stmt.where(SemanticMemory.workspace_id == uuid.UUID(str(workspace_id)))
    return stmt


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/store", status_code=201)
async def store_memory(
    body: MemoryStore,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Store a new semantic memory."""
    memory = SemanticMemory(
        workspace_id=_require_workspace(body.workspace_id),
        content=body.content,
        category=body.category,
        importance=body.importance,
        importance_score=body.importance,
        metadata_=body.metadata or {},
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return _serialise(memory)


@router.post("/recall")
async def recall_memory(
    body: MemoryRecallRequest,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Recall memories matching a query.

    Matching is a case-insensitive substring search; real semantic recall needs
    the embedding pipeline, so `method` names what actually ran rather than
    letting the endpoint imply vector similarity.
    """
    stmt = select(SemanticMemory).where(SemanticMemory.content.ilike(f"%{body.query}%"))
    if body.category:
        stmt = stmt.where(SemanticMemory.category == body.category)
    stmt = _scoped(stmt, body.workspace_id)

    rows = (
        await db.execute(stmt.order_by(SemanticMemory.importance.desc()))
    ).scalars().all()

    # Recall is an access: record it so decay and promotion have real usage to
    # work from rather than a counter that resets with the process.
    now = datetime.now(timezone.utc)
    for row in rows:
        row.access_count = (row.access_count or 0) + 1
        row.last_accessed = now
    await db.commit()

    return {
        "query": body.query,
        "results": [_serialise(r) for r in rows[: body.limit]],
        "total": len(rows),
        "method": "substring_match",
    }


@router.post("/decay")
async def decay_memories(
    threshold: float = Query(0.1, ge=0.0, le=1.0),
    factor: float = Query(0.9, ge=0.0, le=1.0),
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Apply decay to memories at or above a threshold."""
    stmt = _scoped(
        select(SemanticMemory).where(SemanticMemory.importance >= threshold),
        workspace_id,
    )
    rows = (await db.execute(stmt)).scalars().all()

    for row in rows:
        row.importance = row.importance * factor
        row.importance_score = row.importance
    await db.commit()

    return {"decayed_count": len(rows), "factor": factor}


@router.post("/promote/{memory_id}")
async def promote_memory(
    memory_id: str,
    boost: float = Query(0.1, ge=0.0, le=0.5),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Promote a memory by boosting its importance."""
    try:
        mid = uuid.UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Memory not found")

    memory = (
        await db.execute(select(SemanticMemory).where(SemanticMemory.id == mid))
    ).scalar_one_or_none()
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    memory.importance = min(1.0, memory.importance + boost)
    memory.importance_score = memory.importance
    await db.commit()
    await db.refresh(memory)
    return _serialise(memory)


@router.get("/memories")
async def list_memories(
    limit: int = Query(50, ge=1, le=500),
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List stored memories, most important first."""
    stmt = _scoped(select(SemanticMemory), workspace_id)
    rows = (
        await db.execute(
            stmt.order_by(SemanticMemory.importance.desc()).limit(limit)
        )
    ).scalars().all()
    return [_serialise(r) for r in rows]
