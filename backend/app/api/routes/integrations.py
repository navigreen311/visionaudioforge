"""Integration Hub API routes — Slack, Teams, email, webhooks, storage, events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.database import get_async_session
from app.models.settings import WorkspaceIntegration

from app.services.integrations.email import EmailIntegration
from app.services.integrations.event_bus import EventBus
from app.services.integrations.slack import SlackIntegration
from app.services.integrations.storage_connectors import StorageConnectorFactory
from app.services.integrations.teams import TeamsIntegration
from app.services.integrations.webhooks import WebhookManager

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# Shared event bus instance (in-memory for now; inject Redis URL via env)
_event_bus = EventBus()

async def _load_configs(
    db: AsyncSession, workspace_id: str | None
) -> list[WorkspaceIntegration]:
    """All integration rows for one workspace."""
    stmt = select(WorkspaceIntegration)
    stmt = (
        stmt.where(WorkspaceIntegration.workspace_id == uuid.UUID(str(workspace_id)))
        if workspace_id
        else stmt.where(WorkspaceIntegration.workspace_id.is_(None))
    )
    return list((await db.execute(stmt)).scalars().all())


# Integration configs are rows in workspace_integrations. They used to be a
# module-level dict, so a configured Slack webhook or S3 bucket reverted to
# "not connected" on every deploy while the operator believed it was wired up.


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
async def list_integrations(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[IntegrationRecord]:
    """Return all configured integrations with their connection status."""
    stored = {r.type: r for r in await _load_configs(db, workspace_id)}

    records: list[IntegrationRecord] = []
    for itype in IntegrationTypeEnum:
        row = stored.get(itype.value)
        if row:
            cfg = {
                "id": str(row.id),
                "config": row.config or {},
                "updated_at": row.updated_at.isoformat() if row.updated_at else "",
            }
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
async def save_integration(
    body: IntegrationSaveBody,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> IntegrationRecord:
    """Create or update an integration configuration."""
    rows = await _load_configs(db, workspace_id)
    row = next((r for r in rows if r.type == body.type.value), None)

    if row is None:
        row = WorkspaceIntegration(
            workspace_id=uuid.UUID(str(workspace_id)) if workspace_id else None,
            name=body.type.value,
            type=body.type.value,
        )
        db.add(row)

    row.config = body.config
    row.enabled = True
    await db.commit()
    await db.refresh(row)

    return IntegrationRecord(
        id=str(row.id),
        type=body.type,
        status=ConnectionStatusEnum.connected,
        config=_mask_secrets(body.config),
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
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


@router.post("/webhooks", status_code=201)
async def register_webhook(
    body: WebhookRegisterBody,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Register a new outbound webhook."""
    return await WebhookManager.register_webhook(
        db=db,
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
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List webhooks for a workspace."""
    return await WebhookManager.list_webhooks(db=db, workspace_id=workspace_id)


@router.get("/webhooks/{webhook_id}/deliveries")
async def webhook_deliveries(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Recent delivery attempts for a webhook, newest first."""
    return await WebhookManager.delivery_log(db, webhook_id, limit=limit)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a webhook."""
    deleted = await WebhookManager.delete_webhook(db=db, webhook_id=webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"deleted": True}


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Send a test payload to a registered webhook."""
    return await WebhookManager.test_webhook(db, webhook_id)


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
