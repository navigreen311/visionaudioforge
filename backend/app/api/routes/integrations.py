"""Integration Hub API routes — Slack, Teams, email, webhooks, storage, events."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.integrations.email import EmailIntegration
from app.services.integrations.event_bus import EventBus
from app.services.integrations.slack import SlackIntegration
from app.services.integrations.storage_connectors import StorageConnectorFactory
from app.services.integrations.teams import TeamsIntegration
from app.services.integrations.webhooks import WebhookManager

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# Shared event bus instance (in-memory for now; inject Redis URL via env)
_event_bus = EventBus()


# ── Pydantic models ─────────────────────────────────────────────────


class SlackSendBody(BaseModel):
    webhook_url: str
    message: str
    blocks: list[dict[str, Any]] | None = None
    channel: str | None = None


class TeamsSendBody(BaseModel):
    webhook_url: str
    message: str
    card: dict[str, Any] | None = None


class EmailSendBody(BaseModel):
    to: str | list[str]
    subject: str
    body: str
    body_text: str | None = None
    from_addr: str | None = None


class WebhookRegisterBody(BaseModel):
    workspace_id: str
    name: str
    url: str
    events: list[str]
    secret: str | None = None
    headers: dict[str, str] | None = None


class StorageTestBody(BaseModel):
    connector_type: str = Field(..., examples=["s3", "local", "google_drive"])
    config: dict[str, Any] = Field(default_factory=dict)


# ── Slack ────────────────────────────────────────────────────────────


@router.post("/slack/send")
async def slack_send(body: SlackSendBody) -> dict[str, Any]:
    """Send a message to Slack via incoming webhook."""
    result = await SlackIntegration.send_message(
        webhook_url=body.webhook_url,
        text=body.message,
        blocks=body.blocks,
        channel=body.channel,
    )
    return result


# ── Teams ────────────────────────────────────────────────────────────


@router.post("/teams/send")
async def teams_send(body: TeamsSendBody) -> dict[str, Any]:
    """Send a message to Microsoft Teams via incoming webhook."""
    result = await TeamsIntegration.send_message(
        webhook_url=body.webhook_url,
        text=body.message,
        card=body.card,
    )
    return result


# ── Email ────────────────────────────────────────────────────────────


@router.post("/email/send")
async def email_send(body: EmailSendBody) -> dict[str, Any]:
    """Send an email (SMTP → SendGrid → stub)."""
    result = await EmailIntegration.send_email(
        to=body.to,
        subject=body.subject,
        body_html=body.body,
        body_text=body.body_text,
        from_addr=body.from_addr,
    )
    return result


# ── Webhooks ─────────────────────────────────────────────────────────


@router.post("/webhooks")
async def register_webhook(body: WebhookRegisterBody) -> dict[str, Any]:
    """Register a new outbound webhook."""
    return await WebhookManager.register_webhook(
        db=None,
        workspace_id=body.workspace_id,
        name=body.name,
        url=body.url,
        events=body.events,
        secret=body.secret,
        headers=body.headers,
    )


@router.get("/webhooks")
async def list_webhooks(
    workspace_id: str = Query(..., description="Workspace ID"),
) -> list[dict[str, Any]]:
    """List webhooks for a workspace."""
    return await WebhookManager.list_webhooks(db=None, workspace_id=workspace_id)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str) -> dict[str, Any]:
    """Delete a webhook."""
    deleted = await WebhookManager.delete_webhook(db=None, webhook_id=webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"deleted": True}


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str) -> dict[str, Any]:
    """Send a test payload to a registered webhook."""
    return await WebhookManager.test_webhook(webhook_id)


# ── Storage ──────────────────────────────────────────────────────────


@router.post("/storage/test")
async def test_storage(body: StorageTestBody) -> dict[str, Any]:
    """Instantiate a storage connector and run a quick write/read/delete test."""
    try:
        connector = StorageConnectorFactory.get_connector(body.connector_type, body.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    test_key = "__integration_test__"
    test_data = b"integration-hub-test"

    try:
        upload_result = await connector.upload(test_key, test_data)
        downloaded = await connector.download(test_key)
        await connector.delete(test_key)
        return {
            "ok": downloaded == test_data,
            "connector_type": body.connector_type,
            "upload_result": upload_result,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "connector_type": body.connector_type}


# ── Events ───────────────────────────────────────────────────────────


@router.get("/events")
async def list_events(
    limit: int = Query(50, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Return recent events from the event bus log."""
    return _event_bus.recent_events(limit=limit)
