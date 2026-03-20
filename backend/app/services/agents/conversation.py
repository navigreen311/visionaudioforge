"""Conversation history management for the copilot agent."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


class ConversationManager:
    """Store and retrieve conversation history as Event records."""

    async def store_message(
        self,
        db: AsyncSession,
        agent_id: str,
        role: str,
        content: str,
        tool_use: dict | None = None,
        workspace_id: str = "00000000-0000-0000-0000-000000000000",
    ) -> Event:
        """Store a chat message as an Event with type='chat_message'."""
        payload = {
            "agent_id": agent_id,
            "role": role,
            "content": content,
        }
        if tool_use:
            payload["tool_use"] = tool_use

        event = Event(
            type="chat_message",
            payload=payload,
            source="copilot",
            workspace_id=uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    async def get_history(
        self,
        db: AsyncSession,
        agent_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """Get conversation messages ordered by timestamp (oldest first)."""
        stmt = (
            select(Event)
            .where(
                Event.type == "chat_message",
                Event.payload["agent_id"].as_string() == agent_id,
            )
            .order_by(Event.timestamp.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        # Reverse to get chronological order
        events.reverse()

        return [
            {
                "id": str(e.id),
                "role": e.payload.get("role", "unknown") if e.payload else "unknown",
                "content": e.payload.get("content", "") if e.payload else "",
                "tool_use": e.payload.get("tool_use") if e.payload else None,
                "timestamp": e.timestamp.isoformat() if e.timestamp else "",
            }
            for e in events
        ]

    async def get_context_window(
        self,
        db: AsyncSession,
        agent_id: str,
        max_tokens_approx: int = 4000,
    ) -> list[dict]:
        """Get recent messages that fit within an approximate token budget.

        Estimates tokens as len(content) / 4.
        """
        # Fetch a generous limit, then trim by token budget
        all_messages = await self.get_history(db, agent_id, limit=100)

        selected: list[dict] = []
        total_tokens = 0

        # Walk backwards (most recent first), then reverse
        for msg in reversed(all_messages):
            content = msg.get("content", "")
            estimated_tokens = len(content) / 4
            if total_tokens + estimated_tokens > max_tokens_approx:
                break
            selected.append(msg)
            total_tokens += estimated_tokens

        selected.reverse()
        return selected

    async def clear_history(
        self,
        db: AsyncSession,
        agent_id: str,
    ) -> int:
        """Delete all conversation messages for an agent. Returns count deleted."""
        # We need to filter by payload->agent_id, but for bulk delete we fetch IDs first
        stmt = select(Event.id).where(
            Event.type == "chat_message",
            Event.payload["agent_id"].as_string() == agent_id,
        )
        result = await db.execute(stmt)
        ids = [row[0] for row in result.all()]

        if not ids:
            return 0

        del_stmt = delete(Event).where(Event.id.in_(ids))
        del_result = await db.execute(del_stmt)
        await db.commit()
        return del_result.rowcount or 0
