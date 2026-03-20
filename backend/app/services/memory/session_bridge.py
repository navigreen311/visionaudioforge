"""Session Bridge — cross-session continuity via semantic memory."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.semantic_memory import SemanticMemory
from app.services.memory.semantic_memory import SemanticMemoryService


class SessionBridge:
    """Store and retrieve session context for cross-session continuity."""

    SESSION_CATEGORY = "session_context"
    SESSION_TAG = "session_bridge"

    def __init__(self) -> None:
        self._svc = SemanticMemoryService()

    async def save_session_context(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        agent_id: uuid.UUID,
        context: dict[str, Any],
    ) -> SemanticMemory:
        content = json.dumps(
            {"agent_id": str(agent_id), "context": context}, default=str
        )
        return await self._svc.store(
            db=db,
            workspace_id=workspace_id,
            content=content,
            category=self.SESSION_CATEGORY,
            scope="agent",
            importance=0.7,
            source=f"agent:{agent_id}",
            source_type="agent",
            confidence=1.0,
            tags=[self.SESSION_TAG, f"agent:{agent_id}"],
        )

    async def load_session_context(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        stmt = (
            select(SemanticMemory)
            .where(
                and_(
                    SemanticMemory.workspace_id == workspace_id,
                    SemanticMemory.category == self.SESSION_CATEGORY,
                    SemanticMemory.tags.contains([f"agent:{agent_id}"]),
                )
            )
            .order_by(SemanticMemory.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        memory = result.scalar_one_or_none()
        if not memory:
            return None

        try:
            return json.loads(memory.content).get("context")
        except (json.JSONDecodeError, AttributeError):
            return None

    async def build_continuity_prompt(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        agent_id: uuid.UUID,
        n: int = 5,
    ) -> str:
        stmt = (
            select(SemanticMemory)
            .where(
                and_(
                    SemanticMemory.workspace_id == workspace_id,
                    SemanticMemory.category == self.SESSION_CATEGORY,
                    SemanticMemory.tags.contains([f"agent:{agent_id}"]),
                )
            )
            .order_by(SemanticMemory.created_at.desc())
            .limit(n)
        )
        result = await db.execute(stmt)
        memories = list(result.scalars().all())

        if not memories:
            return ""

        # Reverse to chronological order
        memories.reverse()

        lines = ["Previous sessions:"]
        for i, mem in enumerate(memories, 1):
            try:
                ctx = json.loads(mem.content).get("context", {})
                summary = ctx.get("summary", mem.content[:200])
            except (json.JSONDecodeError, AttributeError):
                summary = mem.content[:200]
            lines.append(f"- Session {i}: {summary}")

        return "\n".join(lines)
