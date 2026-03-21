"""Integration Hub API routes — Slack, Teams, email, webhooks, storage, events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
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

# In-memory store for settings-panel integration configs (replace with DB later)
_integration_configs: dict[str, dict[str, Any]] = {}


# ── Enums ──────────────────────────────────────────────────────────


class IntegrationTypeEnum(str, Enum):
    slack = "slack"
    webhook = "webhook"
    s3 = "s3"
    email = "email"


class ConnectionStatusEnum(str, Enum):
    connected = "connected"
    not_connected = "not_connected"


# ── Pydantic models ─────────────────────────────────────────────────


class IntegrationSaveBody(BaseModel):
    type: IntegrationTypeEnum
    config: dict[str, Any] = Field(default_factory=dict)


class IntegrationRecord(BaseModel):
    id: str
    type: IntegrationTypeEnum
    status: ConnectionStatusEnum
    config: dict[str, Any]
    updated_at: str


class IntegrationTestResult(BaseModel):
    ok: bool
    message: str


class SlackTestBody(BaseModel):
    webhook_url: str
    channel: str | None = None


class WebhookTestBody(BaseModel):
    url: str
    headers: dict[str, str] | None = None
    events: list[str] | None = None
    payload_format: str = "json"


class S3TestBody(BaseModel):
    provider: str
    bucket: str
    region: str | None = None
    access_key: str | None = None
    secret_key: str | None = None


class EmailTestBody(BaseModel):
    host: str
    port: int = 587
    username: str | None = None
    use_tls: bool = True


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


# ── Settings-panel integration CRUD ────────────────────────────────


@router.get("")
async def list_integrations() -> list[IntegrationRecord]:
    """Return all configured integrations with their connection status."""
    records: list[IntegrationRecord] = []
    for itype in IntegrationTypeEnum:
        cfg = _integration_configs.get(itype.value)
        if cfg:
            records.append(
                IntegrationRecord(
                    id=cfg.get("id", itype.value),
                    type=itype,
                    status=ConnectionStatusEnum.connected,
                    config=_mask_secrets(cfg.get("config", {})),
                    updated_at=cfg.get("updated_at", ""),
                )
            )
        else:
            records.append(
                IntegrationRecord(
                    id=itype.value,
                    type=itype,
                    status=ConnectionStatusEnum.not_connected,
                    config={},
                    updated_at="",
                )
            )
    return records


@router.post("")
async def save_integration(body: IntegrationSaveBody) -> IntegrationRecord:
    """Create or update an integration configuration."""
    now = datetime.now(timezone.utc).isoformat()
    existing = _integration_configs.get(body.type.value)
    record_id = existing["id"] if existing else str(uuid.uuid4())
    _integration_configs[body.type.value] = {
        "id": record_id,
        "config": body.config,
        "updated_at": now,
    }
    return IntegrationRecord(
        id=record_id,
        type=body.type,
        status=ConnectionStatusEnum.connected,
        config=_mask_secrets(body.config),
        updated_at=now,
    )


@router.post("/slack/test")
async def test_slack_integration(body: SlackTestBody) -> IntegrationTestResult:
    """Test a Slack webhook connection by sending a test message."""
    try:
        await SlackIntegration.send_message(
            webhook_url=body.webhook_url,
            text="VisonAudioForge integration test — connection successful.",
            channel=body.channel,
        )
        return IntegrationTestResult(ok=True, message="Slack test message sent successfully.")
    except Exception as exc:  # noqa: BLE001
        return IntegrationTestResult(ok=False, message=f"Slack test failed: {exc}")


@router.post("/webhook/test")
async def test_webhook_integration(body: WebhookTestBody) -> IntegrationTestResult:
    """Test an outbound webhook by posting a sample payload."""
    import httpx

    payload = {
        "event": "integration.test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {"message": "VisonAudioForge webhook test"},
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                body.url,
                json=payload,
                headers=body.headers or {},
            )
        if resp.status_code < 400:
            return IntegrationTestResult(ok=True, message=f"Webhook responded with {resp.status_code}.")
        return IntegrationTestResult(ok=False, message=f"Webhook returned status {resp.status_code}.")
    except Exception as exc:  # noqa: BLE001
        return IntegrationTestResult(ok=False, message=f"Webhook test failed: {exc}")


@router.post("/s3/test")
async def test_s3_integration(body: S3TestBody) -> IntegrationTestResult:
    """Test object-storage connectivity."""
    connector_map = {"aws": "s3", "gcs": "google_drive", "azure": "azure_blob"}
    connector_type = connector_map.get(body.provider, "s3")
    config: dict[str, Any] = {"bucket": body.bucket}
    if body.region:
        config["region"] = body.region
    if body.access_key:
        config["access_key"] = body.access_key
    try:
        connector = StorageConnectorFactory.get_connector(connector_type, config)
        test_key = "__settings_integration_test__"
        test_data = b"settings-panel-test"
        await connector.upload(test_key, test_data)
        downloaded = await connector.download(test_key)
        await connector.delete(test_key)
        if downloaded == test_data:
            return IntegrationTestResult(ok=True, message="Storage connection verified.")
        return IntegrationTestResult(ok=False, message="Data mismatch during storage test.")
    except Exception as exc:  # noqa: BLE001
        return IntegrationTestResult(ok=False, message=f"Storage test failed: {exc}")


@router.post("/email/test")
async def test_email_integration(body: EmailTestBody) -> IntegrationTestResult:
    """Test SMTP connectivity (attempts EHLO only, no actual send)."""
    import smtplib

    try:
        if body.use_tls:
            server = smtplib.SMTP(body.host, body.port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(body.host, body.port, timeout=10)
        server.ehlo()
        server.quit()
        return IntegrationTestResult(ok=True, message="SMTP connection successful.")
    except Exception as exc:  # noqa: BLE001
        return IntegrationTestResult(ok=False, message=f"SMTP test failed: {exc}")


def _mask_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of config with sensitive fields masked."""
    masked = dict(config)
    for key in ("secret_key", "password", "access_key"):
        if key in masked and masked[key]:
            val = str(masked[key])
            masked[key] = val[:3] + "***" if len(val) > 3 else "***"
    return masked


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
