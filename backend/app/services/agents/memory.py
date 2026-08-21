"""Agent memory service — store, recall, decay, and manage memories."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentMemory


class AgentMemoryService:
    """Manages agent memories with importance scoring and time-based decay."""

    async def store_memory(
        self,
        db: AsyncSession,
        agent_id: str,
        content: str,
        importance_score: float = 0.5,
        category: str | None = None,
    ) -> AgentMemory:
        """Store a new memory for an agent.

        High-importance memories (>= 0.8) never expire.
        Lower-importance memories expire after 30 days.
        """
        expires_at = None
        if importance_score < 0.8:
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        # The console's Save-to-Memory panel offers a category. Accepting it and
        # dropping it would make the selector decorative, so it is stored.
        memory = AgentMemory(
            agent_id=agent_id,
            role="assistant",
            content=content,
            importance_score=importance_score,
            freshness_score=1.0,
            expires_at=expires_at,
            # The console's Save-to-Memory panel offers a category. Accepting it
            # and dropping it would make that selector decorative.
            metadata_={"category": category} if category else {},
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory

    async def recall(
        self,
        db: AsyncSession,
        agent_id: str,
        query: str | None = None,
        k: int = 5,
    ) -> list[AgentMemory]:
        """Recall top-k memories ordered by importance * freshness.

        If query is provided, filter by keyword matching (ILIKE).
        """
        stmt = select(AgentMemory).where(AgentMemory.agent_id == agent_id)

        if query:
            keywords = query.strip().split()
            for keyword in keywords:
                stmt = stmt.where(AgentMemory.content.ilike(f"%{keyword}%"))

        # Order by combined score: importance * freshness descending
        stmt = stmt.order_by(
            (AgentMemory.importance_score * AgentMemory.freshness_score).desc()
        ).limit(k)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def decay_memories(
        self,
        db: AsyncSession,
        agent_id: str,
        decay_factor: float = 0.95,
    ) -> int:
        """Decay all memory freshness scores by the given factor.

        Also deletes expired memories. Returns count of updated memories.
        """
        now = datetime.now(timezone.utc)

        # Delete expired memories
        delete_stmt = delete(AgentMemory).where(
            AgentMemory.agent_id == agent_id,
            AgentMemory.expires_at.isnot(None),
            AgentMemory.expires_at < now,
        )
        await db.execute(delete_stmt)

        # Decay freshness on remaining memories
        update_stmt = (
            update(AgentMemory)
            .where(AgentMemory.agent_id == agent_id)
            .values(freshness_score=AgentMemory.freshness_score * decay_factor)
        )
        result = await db.execute(update_stmt)
        await db.commit()
        return result.rowcount  # type: ignore[return-value]

    async def promote_memory(
        self,
        db: AsyncSession,
        memory_id: str,
        new_importance: float,
    ) -> AgentMemory:
        """Update the importance score of a specific memory."""
        stmt = select(AgentMemory).where(AgentMemory.id == memory_id)
        result = await db.execute(stmt)
        memory = result.scalar_one()

        memory.importance_score = new_importance
        # High importance memories should not expire
        if new_importance >= 0.8:
            memory.expires_at = None

        await db.commit()
        await db.refresh(memory)
        return memory

    async def get_memory_summary(
        self,
        db: AsyncSession,
        agent_id: str,
    ) -> dict:
        """Return a summary of agent memories."""
        base = select(AgentMemory).where(AgentMemory.agent_id == agent_id)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Average importance
        avg_stmt = select(func.avg(AgentMemory.importance_score)).where(
            AgentMemory.agent_id == agent_id
        )
        avg_importance = (await db.execute(avg_stmt)).scalar() or 0.0

        # Recent count (last 24h)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_stmt = (
            select(func.count())
            .where(AgentMemory.agent_id == agent_id)
            .where(AgentMemory.created_at >= recent_cutoff)
        )
        recent_count = (await db.execute(recent_stmt)).scalar() or 0

        # Top memories by combined score
        top_stmt = (
            select(AgentMemory.content)
            .where(AgentMemory.agent_id == agent_id)
            .order_by(
                (AgentMemory.importance_score * AgentMemory.freshness_score).desc()
            )
            .limit(5)
        )
        top_result = await db.execute(top_stmt)
        top_memories = [row[0] for row in top_result.all()]

        return {
            "total_memories": total,
            "avg_importance": round(float(avg_importance), 3),
            "recent_count": recent_count,
            "top_memories": top_memories,
        }

    async def clear_memories(
        self,
        db: AsyncSession,
        agent_id: str,
    ) -> int:
        """Delete all memories for an agent. Returns count deleted."""
        stmt = delete(AgentMemory).where(AgentMemory.agent_id == agent_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount  # type: ignore[return-value]

    async def delete_memory(
        self,
        db: AsyncSession,
        memory_id: str,
    ) -> bool:
        """Delete a specific memory by ID. Returns True if deleted."""
        stmt = delete(AgentMemory).where(AgentMemory.id == memory_id)
        result = await db.execute(stmt)
        await db.commit()
        return (result.rowcount or 0) > 0
