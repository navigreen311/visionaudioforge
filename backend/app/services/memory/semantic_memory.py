"""Core Semantic Memory Service — CRUD, recall with scoring, decay, conflict resolution."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.semantic_memory import MemoryScope, SemanticMemory


class SemanticMemoryService:
    """Workspace-scoped long-term memory with scoring, decay, and privacy."""

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------
    async def store(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        content: str,
        category: str,
        scope: str = "workspace",
        importance: float = 0.5,
        source: str | None = None,
        source_type: str = "system",
        confidence: float = 1.0,
        tags: list[str] | None = None,
        owner_id: uuid.UUID | None = None,
        is_private: bool = False,
        ttl_days: int | None = None,
    ) -> SemanticMemory:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=ttl_days) if ttl_days else None

        memory = SemanticMemory(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            scope=scope,
            category=category,
            content=content,
            importance_score=importance,
            freshness_score=1.0,
            access_count=0,
            source=source,
            source_type=source_type,
            confidence=confidence,
            expires_at=expires_at,
            is_private=is_private,
            owner_id=owner_id,
            tags=tags or [],
            related_memory_ids=[],
        )
        db.add(memory)
        await db.flush()
        return memory

    # ------------------------------------------------------------------
    # Recall
    # ------------------------------------------------------------------
    async def recall(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        query: str,
        scope: str | None = None,
        category: str | None = None,
        k: int = 10,
        min_importance: float = 0.0,
        include_private: bool = False,
        owner_id: uuid.UUID | None = None,
    ) -> list[SemanticMemory]:
        conditions = [
            SemanticMemory.workspace_id == workspace_id,
            SemanticMemory.importance_score >= min_importance,
        ]

        if scope:
            conditions.append(SemanticMemory.scope == scope)
        if category:
            conditions.append(SemanticMemory.category == category)

        # Privacy: exclude private unless owner matches
        if not include_private:
            conditions.append(SemanticMemory.is_private == False)  # noqa: E712
        elif owner_id:
            conditions.append(
                (SemanticMemory.is_private == False)  # noqa: E712
                | (SemanticMemory.owner_id == owner_id)
            )

        # Keyword relevance via ILIKE
        if query.strip():
            conditions.append(SemanticMemory.content.ilike(f"%{query}%"))

        # Score = importance * freshness (relevance is implicit via ILIKE filter)
        score_expr = SemanticMemory.importance_score * SemanticMemory.freshness_score

        stmt = (
            select(SemanticMemory)
            .where(and_(*conditions))
            .order_by(score_expr.desc())
            .limit(k)
        )
        result = await db.execute(stmt)
        memories = list(result.scalars().all())

        # Update access metadata
        now = datetime.now(timezone.utc)
        ids = [m.id for m in memories]
        if ids:
            await db.execute(
                update(SemanticMemory)
                .where(SemanticMemory.id.in_(ids))
                .values(
                    access_count=SemanticMemory.access_count + 1,
                    last_accessed=now,
                )
            )

        return memories

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------
    async def decay_all(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        decay_rate: float = 0.95,
    ) -> dict[str, int]:
        now = datetime.now(timezone.utc)

        # Delete expired memories
        expired_stmt = delete(SemanticMemory).where(
            and_(
                SemanticMemory.workspace_id == workspace_id,
                (SemanticMemory.freshness_score < 0.01)
                | (
                    (SemanticMemory.expires_at != None)  # noqa: E711
                    & (SemanticMemory.expires_at < now)
                ),
            )
        )
        expired_result = await db.execute(expired_stmt)
        expired_count = expired_result.rowcount  # type: ignore[union-attr]

        # Apply decay
        decay_stmt = (
            update(SemanticMemory)
            .where(SemanticMemory.workspace_id == workspace_id)
            .values(freshness_score=SemanticMemory.freshness_score * decay_rate)
        )
        decay_result = await db.execute(decay_stmt)
        decayed_count = decay_result.rowcount  # type: ignore[union-attr]

        return {"decayed": decayed_count, "expired": expired_count}

    # ------------------------------------------------------------------
    # Promote / Demote
    # ------------------------------------------------------------------
    async def promote(
        self,
        db: AsyncSession,
        memory_id: uuid.UUID,
        boost: float = 0.2,
    ) -> SemanticMemory:
        result = await db.execute(
            select(SemanticMemory).where(SemanticMemory.id == memory_id)
        )
        memory = result.scalar_one()
        memory.importance_score = min(1.0, memory.importance_score + boost)
        await db.flush()
        return memory

    async def demote(
        self,
        db: AsyncSession,
        memory_id: uuid.UUID,
        penalty: float = 0.2,
    ) -> SemanticMemory:
        result = await db.execute(
            select(SemanticMemory).where(SemanticMemory.id == memory_id)
        )
        memory = result.scalar_one()
        memory.importance_score = max(0.0, memory.importance_score - penalty)
        await db.flush()
        return memory

    # ------------------------------------------------------------------
    # Conflict Resolution
    # ------------------------------------------------------------------
    async def resolve_conflict(
        self,
        db: AsyncSession,
        memory_id_a: uuid.UUID,
        memory_id_b: uuid.UUID,
    ) -> SemanticMemory:
        result_a = await db.execute(
            select(SemanticMemory).where(SemanticMemory.id == memory_id_a)
        )
        result_b = await db.execute(
            select(SemanticMemory).where(SemanticMemory.id == memory_id_b)
        )
        mem_a = result_a.scalar_one()
        mem_b = result_b.scalar_one()

        if mem_a.confidence >= mem_b.confidence:
            winner, loser = mem_a, mem_b
        else:
            winner, loser = mem_b, mem_a

        # Merge complementary content
        if loser.content not in winner.content:
            winner.content = f"{winner.content}\n[Merged]: {loser.content}"

        # Archive loser
        loser.freshness_score = 0.0
        loser.importance_score = 0.0

        await db.flush()
        return winner

    # ------------------------------------------------------------------
    # Find Related
    # ------------------------------------------------------------------
    async def find_related(
        self,
        db: AsyncSession,
        memory_id: uuid.UUID,
        k: int = 5,
    ) -> list[SemanticMemory]:
        result = await db.execute(
            select(SemanticMemory).where(SemanticMemory.id == memory_id)
        )
        memory = result.scalar_one()

        # Find by tag overlap (same workspace, overlapping tags)
        conditions = [
            SemanticMemory.workspace_id == memory.workspace_id,
            SemanticMemory.id != memory_id,
        ]
        if memory.tags:
            conditions.append(SemanticMemory.tags.overlap(memory.tags))

        stmt = (
            select(SemanticMemory)
            .where(and_(*conditions))
            .order_by(SemanticMemory.importance_score.desc())
            .limit(k)
        )
        result = await db.execute(stmt)
        related = list(result.scalars().all())

        # Fallback: same category if no tag matches
        if not related:
            stmt = (
                select(SemanticMemory)
                .where(
                    and_(
                        SemanticMemory.workspace_id == memory.workspace_id,
                        SemanticMemory.id != memory_id,
                        SemanticMemory.category == memory.category,
                    )
                )
                .order_by(SemanticMemory.importance_score.desc())
                .limit(k)
            )
            result = await db.execute(stmt)
            related = list(result.scalars().all())

        return related

    # ------------------------------------------------------------------
    # Summarize
    # ------------------------------------------------------------------
    async def summarize(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        category: str | None = None,
    ) -> dict[str, Any]:
        base = SemanticMemory.workspace_id == workspace_id
        conditions = [base]
        if category:
            conditions.append(SemanticMemory.category == category)

        where = and_(*conditions)

        # Total count
        total_q = await db.execute(
            select(func.count(SemanticMemory.id)).where(where)
        )
        total = total_q.scalar() or 0

        # By category
        cat_q = await db.execute(
            select(SemanticMemory.category, func.count(SemanticMemory.id))
            .where(base)
            .group_by(SemanticMemory.category)
        )
        by_category = {row[0]: row[1] for row in cat_q.all()}

        # By scope
        scope_q = await db.execute(
            select(SemanticMemory.scope, func.count(SemanticMemory.id))
            .where(base)
            .group_by(SemanticMemory.scope)
        )
        by_scope = {str(row[0]): row[1] for row in scope_q.all()}

        # Averages
        avg_q = await db.execute(
            select(
                func.avg(SemanticMemory.importance_score),
                func.avg(SemanticMemory.freshness_score),
            ).where(where)
        )
        row = avg_q.one()
        avg_importance = float(row[0]) if row[0] else 0.0
        avg_freshness = float(row[1]) if row[1] else 0.0

        # Top memories
        top_q = await db.execute(
            select(SemanticMemory)
            .where(where)
            .order_by(SemanticMemory.importance_score.desc())
            .limit(5)
        )
        top_memories = [
            {"id": str(m.id), "content": m.content[:120], "importance": m.importance_score}
            for m in top_q.scalars().all()
        ]

        # Stale count
        stale_q = await db.execute(
            select(func.count(SemanticMemory.id)).where(
                and_(where, SemanticMemory.freshness_score < 0.1)
            )
        )
        stale_count = stale_q.scalar() or 0

        return {
            "total": total,
            "by_category": by_category,
            "by_scope": by_scope,
            "avg_importance": round(avg_importance, 4),
            "avg_freshness": round(avg_freshness, 4),
            "top_memories": top_memories,
            "stale_count": stale_count,
        }

    # ------------------------------------------------------------------
    # Merge Memories
    # ------------------------------------------------------------------
    async def merge_memories(
        self,
        db: AsyncSession,
        memory_ids: list[uuid.UUID],
        merged_content: str | None = None,
    ) -> SemanticMemory:
        stmt = select(SemanticMemory).where(SemanticMemory.id.in_(memory_ids))
        result = await db.execute(stmt)
        memories = list(result.scalars().all())

        if not memories:
            raise ValueError("No memories found for given IDs")

        # Compute merged values
        best_importance = max(m.importance_score for m in memories)
        avg_confidence = sum(m.confidence for m in memories) / len(memories)
        all_tags: list[str] = []
        for m in memories:
            all_tags.extend(m.tags or [])
        unique_tags = list(set(all_tags))

        if not merged_content:
            merged_content = "\n---\n".join(m.content for m in memories)

        merged = SemanticMemory(
            id=uuid.uuid4(),
            workspace_id=memories[0].workspace_id,
            scope=memories[0].scope,
            category=memories[0].category,
            content=merged_content,
            importance_score=best_importance,
            freshness_score=1.0,
            access_count=0,
            source="merge",
            source_type="system",
            confidence=avg_confidence,
            is_private=any(m.is_private for m in memories),
            owner_id=memories[0].owner_id,
            tags=unique_tags,
            related_memory_ids=[m.id for m in memories],
        )
        db.add(merged)

        # Archive originals
        for m in memories:
            m.freshness_score = 0.0
            m.importance_score = 0.0

        await db.flush()
        return merged

    # ------------------------------------------------------------------
    # Privacy Partition
    # ------------------------------------------------------------------
    async def privacy_partition(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> dict[str, Any]:
        base = SemanticMemory.workspace_id == workspace_id

        pub_q = await db.execute(
            select(func.count(SemanticMemory.id)).where(
                and_(base, SemanticMemory.is_private == False)  # noqa: E712
            )
        )
        public_count = pub_q.scalar() or 0

        priv_q = await db.execute(
            select(func.count(SemanticMemory.id)).where(
                and_(base, SemanticMemory.is_private == True)  # noqa: E712
            )
        )
        private_count = priv_q.scalar() or 0

        owner_q = await db.execute(
            select(SemanticMemory.owner_id, func.count(SemanticMemory.id))
            .where(and_(base, SemanticMemory.is_private == True))  # noqa: E712
            .group_by(SemanticMemory.owner_id)
        )
        by_owner = {str(row[0]): row[1] for row in owner_q.all()}

        return {"public": public_count, "private": private_count, "by_owner": by_owner}

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------
    async def export_memories(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        format: str = "json",
    ) -> list[dict[str, Any]]:
        stmt = (
            select(SemanticMemory)
            .where(SemanticMemory.workspace_id == workspace_id)
            .order_by(SemanticMemory.created_at.desc())
        )
        result = await db.execute(stmt)
        memories = result.scalars().all()

        return [
            {
                "id": str(m.id),
                "content": m.content,
                "category": m.category,
                "scope": str(m.scope),
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
            for m in memories
        ]

    async def import_memories(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        memories: list[dict[str, Any]],
    ) -> dict[str, int]:
        count = 0
        for mem_data in memories:
            memory = SemanticMemory(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                content=mem_data["content"],
                category=mem_data.get("category", "fact"),
                scope=mem_data.get("scope", "workspace"),
                importance_score=mem_data.get("importance_score", 0.5),
                freshness_score=mem_data.get("freshness_score", 1.0),
                access_count=0,
                source=mem_data.get("source"),
                source_type=mem_data.get("source_type", "system"),
                confidence=mem_data.get("confidence", 1.0),
                is_private=mem_data.get("is_private", False),
                tags=mem_data.get("tags", []),
                related_memory_ids=[],
            )
            db.add(memory)
            count += 1
        await db.flush()
        return {"imported": count}

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------
    async def get_memory_timeline(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> list[SemanticMemory]:
        stmt = (
            select(SemanticMemory)
            .where(
                and_(
                    SemanticMemory.workspace_id == workspace_id,
                    SemanticMemory.created_at >= start,
                    SemanticMemory.created_at <= end,
                )
            )
            .order_by(SemanticMemory.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
