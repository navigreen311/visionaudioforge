"""Slack integration — webhook messaging and slash-command handling."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


class SlackIntegration:
    """Send messages to Slack via incoming webhooks and handle slash commands."""

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    @staticmethod
    async def send_message(
        webhook_url: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        """POST a message to a Slack incoming-webhook URL.

        Returns ``{"ok": True/False, "status_code": <int>}``.
        """
        payload: dict[str, Any] = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        if channel:
            payload["channel"] = channel

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(webhook_url, json=payload)

        return {
            "ok": resp.status_code == 200,
            "status_code": resp.status_code,
        }

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def format_alert_message(alert: dict[str, Any]) -> list[dict[str, Any]]:
        """Build Slack Block Kit blocks for an alert notification.

        Layout:
        - Header: severity emoji + title
        - Section: message body
        - Context: timestamp + source
        - Actions: acknowledge button stub
        """
        severity = alert.get("severity", "info").upper()
        emoji = {
            "CRITICAL": ":rotating_light:",
            "HIGH": ":warning:",
            "MEDIUM": ":large_orange_diamond:",
            "LOW": ":information_source:",
            "INFO": ":information_source:",
        }.get(severity, ":bell:")

        title = alert.get("title", "Alert")
        message = alert.get("message", "")
        timestamp = alert.get("timestamp", datetime.now(timezone.utc).isoformat())
        source = alert.get("source", "unknown")

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} [{severity}] {title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"*Timestamp:* {timestamp}"},
                    {"type": "mrkdwn", "text": f"*Source:* {source}"},
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Acknowledge"},
                        "action_id": "acknowledge_alert",
                        "value": str(alert.get("id", "")),
                    }
                ],
            },
        ]

    @staticmethod
    def format_event_notification(event: dict[str, Any]) -> list[dict[str, Any]]:
        """Build Slack blocks for a generic event notification."""
        event_type = event.get("event_type", "unknown.event")
        summary = event.get("summary", "An event occurred.")
        timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":zap: Event: {event_type}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": summary},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"*Timestamp:* {timestamp}"},
                ],
            },
        ]

    # ------------------------------------------------------------------
    # Slash-command receiver
    # ------------------------------------------------------------------

    @staticmethod
    def receive_command(payload: dict[str, Any]) -> dict[str, str]:
        """Parse a Slack slash-command payload and return a response.

        V1 implementation echoes the command text back with a note that
        full command registration is pending.
        """
        command = payload.get("command", "/unknown")
        text = payload.get("text", "")
        user = payload.get("user_name", "someone")

        return {
            "response": (
                f"Received `{command} {text}` from *{user}*. "
                "Command routing is registered — full handler integration coming soon."
            ),
        }
