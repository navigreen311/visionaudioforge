"""Memory Promotion Engine — automatic rules for promoting, demoting, and archiving memories."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.semantic_memory import SemanticMemory
from app.services.memory.semantic_memory import SemanticMemoryService


class MemoryPromotionEngine:
    """Rule-based engine for automatic memory lifecycle management."""

    RULES = [
        {
            "name": "frequent_access",
            "condition": "access_count > 10",
            "action": "promote(0.1)",
        },
        {
            "name": "high_confidence_event",
            "condition": "category == 'event' and confidence > 0.9",
            "action": "promote(0.2)",
        },
        {
            "name": "stale_memory",
            "condition": "freshness < 0.1 and importance < 0.3",
            "action": "archive",
        },
        {
            "name": "user_validated",
            "condition": "source_type == 'user'",
            "action": "promote(0.15)",
        },
        {
            "name": "conflicting_low_confidence",
            "condition": "has_conflict and confidence < 0.5",
            "action": "demote(0.2)",
        },
    ]

    def __init__(self) -> None:
        self._svc = SemanticMemoryService()

    async def apply_rules(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> dict[str, int]:
        stmt = select(SemanticMemory).where(
            SemanticMemory.workspace_id == workspace_id
        )
        result = await db.execute(stmt)
        memories = list(result.scalars().all())

        # Pre-compute conflict set for the workspace
        conflict_pairs = await self.check_conflicts(db, workspace_id)
        conflict_ids: set[uuid.UUID] = set()
        for pair in conflict_pairs:
            conflict_ids.add(pair["memory_a_id"])
            conflict_ids.add(pair["memory_b_id"])

        promotions = 0
        demotions = 0
        archived = 0

        for mem in memories:
            has_conflict = mem.id in conflict_ids

            # Rule: frequent_access
            if mem.access_count > 10:
                mem.importance_score = min(1.0, mem.importance_score + 0.1)
                promotions += 1

            # Rule: high_confidence_event
            if mem.category == "event" and mem.confidence > 0.9:
                mem.importance_score = min(1.0, mem.importance_score + 0.2)
                promotions += 1

            # Rule: stale_memory
            if mem.freshness_score < 0.1 and mem.importance_score < 0.3:
                mem.freshness_score = 0.0
                mem.importance_score = 0.0
                archived += 1

            # Rule: user_validated
            if mem.source_type == "user":
                mem.importance_score = min(1.0, mem.importance_score + 0.15)
                promotions += 1

            # Rule: conflicting_low_confidence
            if has_conflict and mem.confidence < 0.5:
                mem.importance_score = max(0.0, mem.importance_score - 0.2)
                demotions += 1

        await db.flush()
        return {"promotions": promotions, "demotions": demotions, "archived": archived}

    async def check_conflicts(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Find memory pairs with same category and overlapping tags but different content."""
        stmt = select(SemanticMemory).where(
            SemanticMemory.workspace_id == workspace_id
        )
        result = await db.execute(stmt)
        memories = list(result.scalars().all())

        conflicts: list[dict[str, Any]] = []
        seen: set[tuple[uuid.UUID, uuid.UUID]] = set()

        for i, a in enumerate(memories):
            for b in memories[i + 1 :]:
                if a.category != b.category:
                    continue
                # Check tag overlap
                tags_a = set(a.tags or [])
                tags_b = set(b.tags or [])
                if not tags_a or not tags_b:
                    continue
                if not tags_a & tags_b:
                    continue
                # Different content = potential conflict
                if a.content != b.content:
                    pair_key = tuple(sorted([a.id, b.id]))
                    if pair_key not in seen:
                        seen.add(pair_key)
                        conflicts.append(
                            {
                                "memory_a_id": a.id,
                                "memory_b_id": b.id,
                                "category": a.category,
                                "shared_tags": list(tags_a & tags_b),
                            }
                        )

        return conflicts
