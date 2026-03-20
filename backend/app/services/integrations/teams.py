"""Microsoft Teams integration — Adaptive Card messaging via incoming webhooks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


class TeamsIntegration:
    """Send messages and cards to Microsoft Teams via incoming webhooks."""

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    @staticmethod
    async def send_message(
        webhook_url: str,
        text: str,
        card: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST a message (or Adaptive Card) to a Teams incoming-webhook URL.

        Returns ``{"ok": True/False, "status_code": <int>}``.
        """
        if card:
            payload = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": card,
                    }
                ],
            }
        else:
            payload = {"text": text}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(webhook_url, json=payload)

        return {
            "ok": resp.status_code in (200, 202),
            "status_code": resp.status_code,
        }

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def format_alert_card(alert: dict[str, Any]) -> dict[str, Any]:
        """Build a Teams Adaptive Card for an alert notification."""
        severity = alert.get("severity", "info").upper()
        title = alert.get("title", "Alert")
        message = alert.get("message", "")
        timestamp = alert.get("timestamp", datetime.now(timezone.utc).isoformat())
        source = alert.get("source", "unknown")

        severity_color = {
            "CRITICAL": "attention",
            "HIGH": "warning",
            "MEDIUM": "warning",
            "LOW": "good",
            "INFO": "default",
        }.get(severity, "default")

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": f"[{severity}] {title}",
                    "color": severity_color,
                },
                {
                    "type": "TextBlock",
                    "text": message,
                    "wrap": True,
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Timestamp", "value": timestamp},
                        {"title": "Source", "value": source},
                        {"title": "Severity", "value": severity},
                    ],
                },
            ],
        }

    @staticmethod
    def format_summary_card(title: str, stats: dict[str, Any]) -> dict[str, Any]:
        """Build a Teams Adaptive Card summarising key statistics."""
        facts = [{"title": str(k), "value": str(v)} for k, v in stats.items()]

        return {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": title,
                },
                {
                    "type": "FactSet",
                    "facts": facts,
                },
            ],
        }
