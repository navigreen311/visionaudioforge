"""Outbound webhook framework — register, trigger, manage, and verify."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import Webhook, WebhookDelivery


def _as_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _webhook_out(webhook: Webhook, include_secret: bool = False) -> dict[str, Any]:
    payload = {
        "webhook_id": str(webhook.id),
        "workspace_id": (
            str(webhook.workspace_id) if webhook.workspace_id else None
        ),
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events or [],
        "headers": webhook.headers or {},
        "active": webhook.active,
        "failure_count": webhook.failure_count,
        "created_at": (
            webhook.created_at.isoformat() if webhook.created_at else None
        ),
    }
    if include_secret:
        payload["secret"] = webhook.secret
    return payload


class WebhookManager:
    """Manages outbound webhook registrations and delivery.

    Registrations are rows in ``webhooks``: held in class state they were lost
    on restart, so an integration silently stopped firing with nothing to show
    that it had ever been configured. Delivery attempts are recorded in
    ``webhook_deliveries`` so the console's webhook log survives too.
    """

    @staticmethod
    async def _load(db: AsyncSession, webhook_id: str) -> Optional[Webhook]:
        key = _as_uuid(webhook_id)
        if key is None:
            return None
        result = await db.execute(select(Webhook).where(Webhook.id == key))
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @classmethod
    async def register_webhook(
        cls,
        db: AsyncSession,
        workspace_id: str,
        name: str,
        url: str,
        events: list[str],
        secret: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Register a new webhook subscription.

        Supported event patterns: ``alert.*``, ``pipeline.*``, ``model.*``,
        ``asset.*``, or specific events like ``alert.created``.
        """
        webhook = Webhook(
            id=uuid4(),
            workspace_id=_as_uuid(workspace_id),
            name=name,
            url=url,
            events=events,
            secret=secret,
            headers=headers or {},
            active=True,
        )
        db.add(webhook)
        await db.commit()

        return {"webhook_id": str(webhook.id), "events": events}

    # ------------------------------------------------------------------
    # Triggering
    # ------------------------------------------------------------------

    @classmethod
    async def trigger_webhooks(
        cls,
        db: AsyncSession,
        workspace_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fire matching webhooks for *event_type* in *workspace_id*.

        Each webhook whose event list matches receives a POST with the payload
        and an ``X-Signature-256`` header when a secret is configured.
        """
        results: list[dict[str, Any]] = []

        registered = await db.execute(
            select(Webhook).where(
                Webhook.workspace_id == _as_uuid(workspace_id),
                Webhook.active.is_(True),
            )
        )
        matching = [
            w
            for w in registered.scalars().all()
            if cls._event_matches(event_type, w.events or [])
        ]

        body = json.dumps(payload)

        async with httpx.AsyncClient(timeout=10) as client:
            for wh in matching:
                headers = dict(wh.headers or {})
                headers["Content-Type"] = "application/json"
                if wh.secret:
                    sig = cls.compute_signature(body, wh.secret)
                    headers["X-Signature-256"] = f"sha256={sig}"

                start = time.monotonic()
                try:
                    resp = await client.post(wh.url, content=body, headers=headers)
                    latency = (time.monotonic() - start) * 1000
                    succeeded = resp.status_code < 400
                    results.append(
                        {
                            "webhook_id": str(wh.id),
                            "status": "sent",
                            "status_code": resp.status_code,
                            "latency_ms": round(latency, 2),
                        }
                    )
                    cls._record_delivery(
                        db, wh, event_type, payload, succeeded, resp.status_code, None
                    )
                except Exception as exc:  # noqa: BLE001
                    latency = (time.monotonic() - start) * 1000
                    results.append(
                        {
                            "webhook_id": str(wh.id),
                            "status": "failed",
                            "status_code": None,
                            "latency_ms": round(latency, 2),
                        }
                    )
                    cls._record_delivery(
                        db, wh, event_type, payload, False, None, str(exc)
                    )

        if matching:
            await db.commit()

        return results

    @staticmethod
    def _record_delivery(
        db: AsyncSession,
        webhook: Webhook,
        event_type: str,
        payload: dict[str, Any],
        success: bool,
        status_code: int | None,
        error: str | None,
    ) -> None:
        """Stage a delivery record; the caller commits once per trigger."""
        webhook.last_triggered_at = datetime.now(timezone.utc)
        if success:
            webhook.failure_count = 0
        else:
            webhook.failure_count = (webhook.failure_count or 0) + 1

        db.add(
            WebhookDelivery(
                id=uuid4(),
                webhook_id=webhook.id,
                event_type=event_type,
                status_code=status_code,
                success=success,
                error=error,
                payload=payload,
            )
        )

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    @classmethod
    async def list_webhooks(
        cls, db: AsyncSession, workspace_id: str
    ) -> list[dict[str, Any]]:
        """Return all webhook configs for a workspace, secrets omitted."""
        result = await db.execute(
            select(Webhook)
            .where(Webhook.workspace_id == _as_uuid(workspace_id))
            .order_by(Webhook.created_at)
        )
        return [_webhook_out(w) for w in result.scalars().all()]

    @classmethod
    async def delivery_log(
        cls, db: AsyncSession, webhook_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return recent delivery attempts for a webhook, newest first."""
        webhook = await cls._load(db, webhook_id)
        if webhook is None:
            return []

        result = await db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == webhook.id)
            .order_by(WebhookDelivery.timestamp.desc())
            .limit(limit)
        )
        return [
            {
                "id": str(d.id),
                "event_type": d.event_type,
                "success": d.success,
                "status_code": d.status_code,
                "error": d.error,
                "timestamp": d.timestamp.isoformat() if d.timestamp else None,
            }
            for d in result.scalars().all()
        ]

    @classmethod
    async def delete_webhook(cls, db: AsyncSession, webhook_id: str) -> bool:
        """Remove a webhook registration.  Returns *True* if it existed."""
        webhook = await cls._load(db, webhook_id)
        if webhook is None:
            return False

        await db.delete(webhook)
        await db.commit()
        return True

    @classmethod
    async def test_webhook(
        cls, db: AsyncSession, webhook_id: str
    ) -> dict[str, Any]:
        """Send a test payload to a registered webhook."""
        wh = await cls._load(db, webhook_id)
        if not wh:
            return {"ok": False, "error": "Webhook not found"}

        test_payload = {
            "event_type": "webhook.test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"message": "Test delivery from VAF Integration Hub"},
        }
        body = json.dumps(test_payload)
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if wh.secret:
            sig = cls.compute_signature(body, wh.secret)
            headers["X-Signature-256"] = f"sha256={sig}"

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(wh.url, content=body, headers=headers)
            latency = (time.monotonic() - start) * 1000
            return {
                "ok": resp.status_code < 400,
                "status_code": resp.status_code,
                "latency_ms": round(latency, 2),
            }
        except Exception as exc:  # noqa: BLE001
            latency = (time.monotonic() - start) * 1000
            return {"ok": False, "error": str(exc), "latency_ms": round(latency, 2)}

    # ------------------------------------------------------------------
    # Signature
    # ------------------------------------------------------------------

    @staticmethod
    def compute_signature(payload: str, secret: str) -> str:
        """HMAC-SHA256 hex digest of *payload* using *secret*."""
        return hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _event_matches(event_type: str, patterns: list[str]) -> bool:
        """Check if *event_type* matches any of the registered *patterns*.

        Supports exact match and wildcard suffix (e.g. ``alert.*``).
        """
        for p in patterns:
            if p == event_type:
                return True
            if p.endswith(".*"):
                prefix = p[:-2]
                if event_type.startswith(prefix + "."):
                    return True
        return False

    @classmethod
    async def _reset(cls, db: AsyncSession) -> None:
        """Delete every webhook registration (for tests)."""
        for webhook in (await db.execute(select(Webhook))).scalars().all():
            await db.delete(webhook)
        await db.commit()
