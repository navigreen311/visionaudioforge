"""AlertActionExecutor — dispatches alert notifications to configured channels.

Supports webhook, email (real SMTP or stub), Slack, Discord, SMS stub,
and log actions with retry logic and exponential backoff.
"""

import asyncio
import json
import logging
import os
import smtplib
import time
from email.mime.text import MIMEText
from typing import Any

import httpx

from app.models.alert import Alert

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1  # 1s, 2s, 4s


async def _retry_async(coro_factory, retries: int = MAX_RETRIES):
    """Retry an async callable with exponential backoff.

    coro_factory is a zero-arg callable that returns an awaitable.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                wait = BACKOFF_BASE_SECONDS * (2 ** attempt)
                logger.warning(
                    "Delivery attempt %d failed (%s), retrying in %ss...",
                    attempt + 1,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)
    raise last_exc  # type: ignore[misc]


class AlertActionExecutor:
    """Execute alert actions (webhook, email, slack, discord, sms, log) for a triggered alert."""

    @staticmethod
    async def execute_actions(
        alert: Alert,
        actions_config: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Run all configured actions for an alert. Returns result list."""
        results: list[dict[str, Any]] = []
        for action_cfg in actions_config:
            action_type = action_cfg.get("type", "log")
            config = action_cfg.get("config", {})
            try:
                if action_type == "webhook":
                    result = await send_webhook(
                        url=config["url"],
                        payload=AlertActionExecutor._build_payload(alert),
                        headers=config.get("headers"),
                        timeout=config.get("timeout", 10),
                    )
                    results.append({"action": action_type, "status": "sent", "error": None, **result})
                elif action_type == "email":
                    result = await send_email(
                        to=config.get("to", "admin@example.com"),
                        subject=f"Alert: {alert.payload.get('rule_name', 'Unknown')}",
                        body=json.dumps(AlertActionExecutor._build_payload(alert), default=str),
                        smtp_config=config.get("smtp_config"),
                    )
                    results.append({"action": action_type, **result, "error": None})
                elif action_type == "slack":
                    result = await send_slack(
                        webhook_url=config["webhook_url"],
                        message=AlertActionExecutor._format_slack_message(alert),
                        blocks=AlertActionExecutor._build_slack_blocks(alert),
                    )
                    results.append({"action": action_type, **result, "error": None})
                elif action_type == "discord":
                    result = await send_discord(
                        webhook_url=config["webhook_url"],
                        message=AlertActionExecutor._format_discord_message(alert),
                        embeds=AlertActionExecutor._build_discord_embeds(alert),
                    )
                    results.append({"action": action_type, **result, "error": None})
                elif action_type == "sms":
                    result = await send_sms_stub(
                        to=config.get("to", ""),
                        message=AlertActionExecutor._format_sms_message(alert),
                    )
                    results.append({"action": action_type, **result, "error": None})
                elif action_type == "log":
                    await AlertActionExecutor.log_alert(alert)
                    results.append({"action": action_type, "status": "sent", "error": None})
                else:
                    raise ValueError(f"Unknown action type: {action_type}")

            except Exception as exc:
                logger.error("Action %s failed for alert %s: %s", action_type, alert.id, exc)
                results.append({"action": action_type, "status": "failed", "error": str(exc)})
        return results

    @staticmethod
    async def log_alert(alert: Alert) -> None:
        """Write a structured log entry for the alert."""
        logger.info(
            "ALERT id=%s severity=%s status=%s rule=%s payload=%s",
            alert.id,
            alert.severity.value if hasattr(alert.severity, "value") else alert.severity,
            alert.status.value if hasattr(alert.status, "value") else alert.status,
            alert.rule_id,
            json.dumps(alert.payload, default=str) if alert.payload else "{}",
        )

    @staticmethod
    def _build_payload(alert: Alert) -> dict[str, Any]:
        """Build a serialisable payload dict from an Alert object."""
        return {
            "alert_id": str(alert.id),
            "rule_id": str(alert.rule_id),
            "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
            "status": alert.status.value if hasattr(alert.status, "value") else str(alert.status),
            "payload": alert.payload or {},
            "workspace_id": str(alert.workspace_id),
        }

    @staticmethod
    def _format_slack_message(alert: Alert) -> str:
        """Format a human-readable Slack message for an alert."""
        sev = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        rule_name = (alert.payload or {}).get("rule_name", "Unknown rule")
        metric = (alert.payload or {}).get("metric", "N/A")
        value = (alert.payload or {}).get("metric_value", "N/A")
        return (
            f":rotating_light: *Alert Triggered*\n"
            f"*Rule:* {rule_name}\n"
            f"*Severity:* {sev}\n"
            f"*Metric:* {metric} = {value}\n"
            f"*Alert ID:* {alert.id}"
        )

    @staticmethod
    def _build_slack_blocks(alert: Alert) -> list[dict[str, Any]]:
        """Build Slack Block Kit blocks for rich formatting."""
        sev = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        rule_name = (alert.payload or {}).get("rule_name", "Unknown rule")
        metric = (alert.payload or {}).get("metric", "N/A")
        value = (alert.payload or {}).get("metric_value", "N/A")

        severity_emoji = {
            "critical": ":red_circle:",
            "high": ":large_orange_circle:",
            "medium": ":large_yellow_circle:",
            "low": ":large_blue_circle:",
        }.get(sev, ":white_circle:")

        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Alert: {rule_name}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity_emoji} {sev.upper()}"},
                    {"type": "mrkdwn", "text": f"*Metric:*\n{metric} = {value}"},
                    {"type": "mrkdwn", "text": f"*Alert ID:*\n`{alert.id}`"},
                    {"type": "mrkdwn", "text": f"*Timestamp:*\n{timestamp}"},
                ],
            },
        ]

    @staticmethod
    def _format_discord_message(alert: Alert) -> str:
        """Format a Discord message."""
        sev = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        rule_name = (alert.payload or {}).get("rule_name", "Unknown rule")
        return f"**Alert Triggered** | {rule_name} | Severity: {sev.upper()}"

    @staticmethod
    def _build_discord_embeds(alert: Alert) -> list[dict[str, Any]]:
        """Build Discord embed objects for rich formatting."""
        sev = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        rule_name = (alert.payload or {}).get("rule_name", "Unknown rule")
        metric = (alert.payload or {}).get("metric", "N/A")
        value = (alert.payload or {}).get("metric_value", "N/A")

        color_map = {"critical": 0xFF0000, "high": 0xFF8C00, "medium": 0xFFD700, "low": 0x4169E1}
        color = color_map.get(sev, 0x808080)

        from datetime import datetime, timezone

        return [
            {
                "title": f"Alert: {rule_name}",
                "color": color,
                "fields": [
                    {"name": "Severity", "value": sev.upper(), "inline": True},
                    {"name": "Metric", "value": f"{metric} = {value}", "inline": True},
                    {"name": "Alert ID", "value": str(alert.id), "inline": False},
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

    @staticmethod
    def _format_sms_message(alert: Alert) -> str:
        """Format a short SMS message."""
        sev = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        rule_name = (alert.payload or {}).get("rule_name", "Unknown rule")
        return f"[{sev.upper()}] Alert: {rule_name} (ID: {alert.id})"


# ======================================================================
# Standalone delivery functions (used by routes and action executor)
# ======================================================================


async def send_webhook(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    """POST alert payload to a webhook URL with retry logic.

    Returns {"status": "sent", "status_code": int, "response_time_ms": float}
    """
    async def _do_send():
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        elapsed_ms = (time.monotonic() - start) * 1000
        return {
            "status": "sent",
            "status_code": resp.status_code,
            "response_time_ms": round(elapsed_ms, 2),
        }

    result = await _retry_async(_do_send)
    logger.info("Webhook sent to %s (status %s, %.1fms)", url, result["status_code"], result["response_time_ms"])
    return result


async def send_email(
    to: str,
    subject: str,
    body: str,
    smtp_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send an email via SMTP if configured, otherwise return a stub.

    Uses SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS env vars if smtp_config not provided.
    """
    smtp_host = os.environ.get("SMTP_HOST", "")
    if smtp_config:
        smtp_host = smtp_config.get("host", smtp_host)

    if not smtp_host:
        logger.info("EMAIL STUB [to=%s, subject=%s]: %s", to, subject, body[:200])
        return {"status": "stub", "note": "Set SMTP_HOST env var for real email delivery"}

    # Real SMTP delivery
    smtp_port = int(smtp_config.get("port", os.environ.get("SMTP_PORT", "587")) if smtp_config else os.environ.get("SMTP_PORT", "587"))
    smtp_user = (smtp_config or {}).get("user", os.environ.get("SMTP_USER", ""))
    smtp_pass = (smtp_config or {}).get("password", os.environ.get("SMTP_PASS", ""))
    from_addr = (smtp_config or {}).get("from", smtp_user or "alerts@system.local")

    def _send_sync():
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            if smtp_port == 587:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, [to], msg.as_string())

    await asyncio.get_event_loop().run_in_executor(None, _send_sync)
    logger.info("Email sent to %s (subject=%s)", to, subject)
    return {"status": "sent", "note": f"Delivered via {smtp_host}:{smtp_port}"}


async def send_slack(
    webhook_url: str,
    message: str,
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """POST a message to a Slack incoming webhook with blocks support and retry.

    Returns {"status": "sent", "status_code": int}
    """
    payload: dict[str, Any] = {"text": message}
    if blocks:
        payload["blocks"] = blocks

    async def _do_send():
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        return {"status": "sent", "status_code": resp.status_code}

    result = await _retry_async(_do_send)
    logger.info("Slack notification sent (status %s)", result["status_code"])
    return result


async def send_sms_stub(
    to: str,
    message: str,
) -> dict[str, Any]:
    """SMS delivery stub. Set TWILIO_SID and TWILIO_TOKEN for real delivery.

    Returns {"status": "stub", "note": str}
    """
    twilio_sid = os.environ.get("TWILIO_SID", "")
    twilio_token = os.environ.get("TWILIO_TOKEN", "")

    if twilio_sid and twilio_token:
        logger.info("SMS would be sent to %s via Twilio (SID=%s...)", to, twilio_sid[:8])
        return {"status": "stub", "note": "Twilio credentials present but SDK not installed. Install twilio package for real SMS."}

    logger.info("SMS STUB [to=%s]: %s", to, message[:100])
    return {"status": "stub", "note": "Set TWILIO_SID and TWILIO_TOKEN for SMS delivery"}


async def send_discord(
    webhook_url: str,
    message: str,
    embeds: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """POST a message to a Discord webhook with embed support and retry.

    Returns {"status": "sent", "status_code": int}
    """
    payload: dict[str, Any] = {"content": message}
    if embeds:
        payload["embeds"] = embeds

    async def _do_send():
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        return {"status": "sent", "status_code": resp.status_code}

    result = await _retry_async(_do_send)
    logger.info("Discord notification sent (status %s)", result["status_code"])
    return result
