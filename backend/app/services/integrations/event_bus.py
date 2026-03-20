"""Event bus — Redis pub/sub with webhook triggering and event logging."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

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
    ) -> None:
        """Central event emission point.

        1. Publish to the workspace's Redis channel.
        2. Trigger any registered outbound webhooks.
        3. Append to the local event log.
        """
        from app.services.integrations.webhooks import WebhookManager

        channel = f"workspace:{workspace_id}"
        await self.publish(channel, event_type, payload)

        # Fire outbound webhooks (best-effort)
        try:
            await WebhookManager.trigger_webhooks(None, workspace_id, event_type, payload)
        except Exception:  # noqa: BLE001
            logger.exception("Webhook trigger failed for %s", event_type)

        # Append to in-memory log
        self._event_log.append(
            {
                "workspace_id": workspace_id,
                "event_type": event_type,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    # ------------------------------------------------------------------
    # Log access
    # ------------------------------------------------------------------

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent events from the in-memory log."""
        return list(reversed(self._event_log[-limit:]))
