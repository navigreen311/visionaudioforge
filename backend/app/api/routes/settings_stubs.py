"""Settings stub routes - general, security, notifications, team management."""

from __future__ import annotations

from typing import Any

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.deps import get_db, get_workspace_id
from app.models.integration import Webhook, WebhookDelivery
from app.models.settings import WorkspaceSetting

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GeneralSettings(BaseModel):
    project_name: str = "VisonAudioForge"
    description: str = "Vision & Audio AI Platform"
    default_workspace: str = "main"
    auto_save: bool = True
    max_upload_mb: int = 500


class SecuritySettings(BaseModel):
    mfa_enabled: bool = False
    session_timeout_min: int = 60
    password_policy: str = "strong"
    ip_whitelist: list[str] = Field(default_factory=list)
    api_key_rotation_days: int = 90


class NotificationSettings(BaseModel):
    email_alerts: bool = True
    slack_webhook: str = ""
    alert_on_failure: bool = True
    alert_on_drift: bool = True
    digest_frequency: str = "daily"


class TeamMember(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    joined_at: str


# ---------------------------------------------------------------------------
# Storage
#
# These three were module-level dicts seeded from the Pydantic defaults, so
# every save was forgotten on restart and the console showed the defaults
# again as though nothing had been configured. Each section is now a row in
# workspace_settings.
# ---------------------------------------------------------------------------


async def _read_section(
    db: AsyncSession, workspace_id: UUID, section: str, model: type[BaseModel]
) -> BaseModel:
    """Return a settings section, falling back to its defaults."""
    result = await db.execute(
        select(WorkspaceSetting).where(
            WorkspaceSetting.workspace_id == workspace_id,
            WorkspaceSetting.section == section,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return model()
    # Defaults fill in any field added since the row was written.
    return model(**{**model().model_dump(), **(row.value or {})})


async def _write_section(
    db: AsyncSession, workspace_id: UUID, section: str, payload: BaseModel
) -> BaseModel:
    """Persist a settings section and return what was stored."""
    result = await db.execute(
        select(WorkspaceSetting).where(
            WorkspaceSetting.workspace_id == workspace_id,
            WorkspaceSetting.section == section,
        )
    )
    row = result.scalar_one_or_none()
    value = payload.model_dump()

    if row is None:
        db.add(
            WorkspaceSetting(
                workspace_id=workspace_id, section=section, value=value
            )
        )
    else:
        row.value = {**(row.value or {}), **value}

    await db.commit()
    return payload


# ---------------------------------------------------------------------------
# Routes - General
# ---------------------------------------------------------------------------

@router.get("/general", response_model=GeneralSettings)
async def get_general(
    workspace_id: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    """Return general platform settings."""
    return await _read_section(db, workspace_id, "general", GeneralSettings)


@router.put("/general", response_model=GeneralSettings)
async def update_general(
    body: GeneralSettings,
    workspace_id: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    """Update general platform settings."""
    return await _write_section(db, workspace_id, "general", body)


# ---------------------------------------------------------------------------
# Routes - Security
# ---------------------------------------------------------------------------

@router.get("/security", response_model=SecuritySettings)
async def get_security(
    workspace_id: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    """Return security settings."""
    return await _read_section(db, workspace_id, "security", SecuritySettings)


@router.put("/security", response_model=SecuritySettings)
async def update_security(
    body: SecuritySettings,
    workspace_id: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    """Update security settings."""
    return await _write_section(db, workspace_id, "security", body)


# ---------------------------------------------------------------------------
# Routes - Notifications
# ---------------------------------------------------------------------------

@router.get("/notifications", response_model=NotificationSettings)
async def get_notifications(
    workspace_id: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    """Return notification preferences."""
    return await _read_section(db, workspace_id, "notifications", NotificationSettings)


@router.put("/notifications", response_model=NotificationSettings)
async def update_notifications(
    body: NotificationSettings,
    workspace_id: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    """Update notification preferences."""
    return await _write_section(db, workspace_id, "notifications", body)


# ---------------------------------------------------------------------------
# Routes - Team
# ---------------------------------------------------------------------------

@router.get("/integrations/webhook/logs")
async def get_webhook_logs(
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
):
    """Recent webhook delivery attempts for this workspace.

    This returned three fixed entries dated April 2026, so the integrations
    screen showed deliveries that never happened and hid the ones that did.
    `webhook_deliveries` has been recording the real attempts.
    """
    rows = (
        await db.execute(
            select(WebhookDelivery)
            .join(Webhook, Webhook.id == WebhookDelivery.webhook_id)
            .where(Webhook.workspace_id == session_workspace)
            .order_by(WebhookDelivery.id.desc())
            .limit(100)
        )
    ).scalars().all()

    return {
        "logs": [
            {
                "id": str(d.id),
                "event": d.event_type,
                "status": "delivered" if d.success else "failed",
                "response_code": d.status_code,
                "error": d.error,
                "timestamp": (
                    d.delivered_at.isoformat() if getattr(d, "delivered_at", None) else ""
                ),
            }
            for d in rows
        ]
    }


@router.post("/integrations/webhook/retry")
async def retry_webhook(body: dict):
    """Retry a failed webhook delivery."""
    return {"success": True, "delivery_id": body.get("delivery_id")}
