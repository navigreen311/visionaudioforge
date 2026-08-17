"""Event bus — Redis pub/sub with webhook triggering and event logging."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import EventLogEntry

logger = logging.getLogger(__name__)


def _as_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None

# Well-known event types
EVENT_TYPES = [
    "alert.created",
    "alert.acknowledged",
    "pipeline.started",
    "pipeline.completed",
    "model.registered",
    "model.promoted",
    "asset.uploaded",
    "capture.started",
]


class EventBus:
    """Central event bus backed by Redis pub/sub.

    If Redis is unavailable the bus operates in a degraded in-memory mode
    so that tests and local development still work.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url
        self._redis: Any | None = None
        self._subscriptions: dict[str, list[Callable[..., Any]]] = {}
        self._event_log: list[dict[str, Any]] = []

        if redis_url:
            try:
                import redis.asyncio as aioredis  # type: ignore[import-untyped]

                self._redis = aioredis.from_url(redis_url)
            except Exception:  # noqa: BLE001
                logger.warning("Redis unavailable at %s — falling back to in-memory bus", redis_url)

    # ------------------------------------------------------------------
    # Pub / Sub
    # ------------------------------------------------------------------

    async def publish(self, channel: str, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event to *channel*."""
        message = {
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self._redis:
            await self._redis.publish(channel, json.dumps(message))
        else:
            # In-memory fallback: call local subscribers
            for cb in self._subscriptions.get(channel, []):
                try:
                    await cb(message)
                except Exception:  # noqa: BLE001
                    logger.exception("Subscriber callback failed")

    async def subscribe(self, channel: str, callback: Callable[..., Any]) -> dict[str, Any]:
        """Register *callback* for events on *channel*.

        With Redis this sets up a pubsub subscription; without Redis it
        stores the callback for in-memory dispatch.
        """
        self._subscriptions.setdefault(channel, []).append(callback)

        if self._redis:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(channel)
            return {"channel": channel, "status": "subscribed", "backend": "redis"}

        return {"channel": channel, "status": "subscribed", "backend": "memory"}

    # ------------------------------------------------------------------
    # High-level emit
    # ------------------------------------------------------------------

    async def emit(
        self,
        workspace_id: str,
        event_type: str,
        payload: dict[str, Any],
        db: "AsyncSession | None" = None,
    ) -> None:
        """Central event emission point.

        1. Publish to the workspace's Redis channel.
        2. Trigger any registered outbound webhooks.
        3. Append to the local event log.
        """
        from app.services.integrations.webhooks import WebhookManager

        channel = f"workspace:{workspace_id}"
        await self.publish(channel, event_type, payload)

        # Fire outbound webhooks (best-effort) and record the event. Both need
        # a session; without one the bus still publishes, but nothing durable
        # is written, so callers that care pass db.
        if db is not None:
            try:
                await WebhookManager.trigger_webhooks(
                    db, workspace_id, event_type, payload
                )
            except Exception:  # noqa: BLE001
                logger.exception("Webhook trigger failed for %s", event_type)

            db.add(
                EventLogEntry(
                    id=uuid4(),
                    workspace_id=_as_uuid(workspace_id),
                    event_type=event_type,
                    payload=payload,
                )
            )
            await db.commit()

        # Process-local mirror so recent_events() works without a session.
        self._event_log.append(
            {
                "workspace_id": workspace_id,
                "event_type": event_type,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        del self._event_log[:-500]

    # ------------------------------------------------------------------
    # Log access
    # ------------------------------------------------------------------

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent events seen by *this* process.

        Only what this worker published. For the workspace-wide view every
        worker agrees on, use :meth:`recent_events_stored`.
        """
        return list(reversed(self._event_log[-limit:]))

    @staticmethod
    async def recent_events_stored(
        db: "AsyncSession",
        workspace_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return recent events from the durable log, newest first."""
        query = select(EventLogEntry).order_by(EventLogEntry.timestamp.desc())
        if workspace_id is not None:
            query = query.where(EventLogEntry.workspace_id == _as_uuid(workspace_id))

        result = await db.execute(query.limit(limit))
        return [
            {
                "workspace_id": (
                    str(e.workspace_id) if e.workspace_id else None
                ),
                "event_type": e.event_type,
                "payload": e.payload,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in result.scalars().all()
        ]
