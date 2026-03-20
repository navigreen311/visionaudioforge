"""Outbound webhook framework — register, trigger, manage, and verify."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx


class WebhookManager:
    """Manages outbound webhook registrations and delivery."""

    # In-memory store; swap for DB-backed persistence as needed.
    _webhooks: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @classmethod
    async def register_webhook(
        cls,
        db: Any,  # noqa: ARG003 — reserved for DB session
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
        webhook_id = str(uuid.uuid4())
        record = {
            "webhook_id": webhook_id,
            "workspace_id": workspace_id,
            "name": name,
            "url": url,
            "events": events,
            "secret": secret,
            "headers": headers or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        cls._webhooks[webhook_id] = record
        return {"webhook_id": webhook_id, "events": events}

    # ------------------------------------------------------------------
    # Triggering
    # ------------------------------------------------------------------

    @classmethod
    async def trigger_webhooks(
        cls,
        db: Any,  # noqa: ARG003
        workspace_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fire matching webhooks for *event_type* in *workspace_id*.

        Each webhook whose event list matches receives a POST with the payload
        and an ``X-Signature-256`` header when a secret is configured.
        """
        results: list[dict[str, Any]] = []
        matching = [
            w
            for w in cls._webhooks.values()
            if w["workspace_id"] == workspace_id
            and cls._event_matches(event_type, w["events"])
        ]

        body = json.dumps(payload)

        async with httpx.AsyncClient(timeout=10) as client:
            for wh in matching:
                headers = dict(wh.get("headers") or {})
                headers["Content-Type"] = "application/json"
                if wh.get("secret"):
                    sig = cls.compute_signature(body, wh["secret"])
                    headers["X-Signature-256"] = f"sha256={sig}"

                start = time.monotonic()
                try:
                    resp = await client.post(wh["url"], content=body, headers=headers)
                    latency = (time.monotonic() - start) * 1000
                    results.append(
                        {
                            "webhook_id": wh["webhook_id"],
                            "status": "sent",
                            "status_code": resp.status_code,
                            "latency_ms": round(latency, 2),
                        }
                    )
                except Exception:  # noqa: BLE001
                    latency = (time.monotonic() - start) * 1000
                    results.append(
                        {
                            "webhook_id": wh["webhook_id"],
                            "status": "failed",
                            "status_code": None,
                            "latency_ms": round(latency, 2),
                        }
                    )

        return results

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    @classmethod
    async def list_webhooks(
        cls, db: Any, workspace_id: str  # noqa: ARG003
    ) -> list[dict[str, Any]]:
        """Return all webhook configs for a workspace."""
        return [
            {k: v for k, v in w.items() if k != "secret"}
            for w in cls._webhooks.values()
            if w["workspace_id"] == workspace_id
        ]

    @classmethod
    async def delete_webhook(
        cls, db: Any, webhook_id: str  # noqa: ARG003
    ) -> bool:
        """Remove a webhook registration.  Returns *True* if it existed."""
        return cls._webhooks.pop(webhook_id, None) is not None

    @classmethod
    async def test_webhook(
        cls, webhook_id: str
    ) -> dict[str, Any]:
        """Send a test payload to a registered webhook."""
        wh = cls._webhooks.get(webhook_id)
        if not wh:
            return {"ok": False, "error": "Webhook not found"}

        test_payload = {
            "event_type": "webhook.test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"message": "Test delivery from VAF Integration Hub"},
        }
        body = json.dumps(test_payload)
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if wh.get("secret"):
            sig = cls.compute_signature(body, wh["secret"])
            headers["X-Signature-256"] = f"sha256={sig}"

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(wh["url"], content=body, headers=headers)
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
    def _reset(cls) -> None:
        """Reset in-memory store (for tests)."""
        cls._webhooks.clear()
