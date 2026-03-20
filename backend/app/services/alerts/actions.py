"""AlertActionExecutor — dispatches alert notifications to configured channels."""

import json
import logging
from typing import Any

import httpx

from app.models.alert import Alert

logger = logging.getLogger(__name__)


class AlertActionExecutor:
    """Execute alert actions (webhook, email, slack, log) for a triggered alert."""

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
                    await AlertActionExecutor.send_webhook(
                        url=config["url"],
                        payload=AlertActionExecutor._build_payload(alert),
                    )
                elif action_type == "email":
                    await AlertActionExecutor.send_email(
                        to=config.get("to", "admin@example.com"),
                        subject=f"Alert: {alert.payload.get('rule_name', 'Unknown')}",
                        body=json.dumps(AlertActionExecutor._build_payload(alert), default=str),
                    )
                elif action_type == "slack":
                    await AlertActionExecutor.send_slack(
                        webhook_url=config["webhook_url"],
                        message=AlertActionExecutor._format_slack_message(alert),
                    )
                elif action_type == "log":
                    await AlertActionExecutor.log_alert(alert)
                else:
                    raise ValueError(f"Unknown action type: {action_type}")

                results.append({"action": action_type, "status": "sent", "error": None})
            except Exception as exc:
                logger.error("Action %s failed for alert %s: %s", action_type, alert.id, exc)
                results.append({"action": action_type, "status": "failed", "error": str(exc)})
        return results

    @staticmethod
    async def send_webhook(url: str, payload: dict[str, Any]) -> None:
        """POST alert payload to a webhook URL."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Webhook sent to %s (status %s)", url, resp.status_code)

    @staticmethod
    async def send_email(to: str, subject: str, body: str) -> None:
        """Placeholder email sender — logs instead of sending."""
        logger.info("EMAIL [to=%s, subject=%s]: %s", to, subject, body[:200])

    @staticmethod
    async def send_slack(webhook_url: str, message: str) -> None:
        """POST a message to a Slack incoming webhook."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json={"text": message})
            resp.raise_for_status()
        logger.info("Slack notification sent")

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
