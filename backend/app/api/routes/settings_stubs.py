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
# In-memory state
# ---------------------------------------------------------------------------

_general: dict[str, Any] = GeneralSettings().model_dump()
_security: dict[str, Any] = SecuritySettings().model_dump()
_notifications: dict[str, Any] = NotificationSettings().model_dump()


# ---------------------------------------------------------------------------
# Routes - General
# ---------------------------------------------------------------------------

@router.get("/general", response_model=GeneralSettings)
async def get_general():
    """Return general platform settings."""
    return GeneralSettings(**_general)


@router.put("/general", response_model=GeneralSettings)
async def update_general(body: GeneralSettings):
    """Update general platform settings."""
    _general.update(body.model_dump())
    return GeneralSettings(**_general)


# ---------------------------------------------------------------------------
# Routes - Security
# ---------------------------------------------------------------------------

@router.get("/security", response_model=SecuritySettings)
async def get_security():
    """Return security settings."""
    return SecuritySettings(**_security)


@router.put("/security", response_model=SecuritySettings)
async def update_security(body: SecuritySettings):
    """Update security settings."""
    _security.update(body.model_dump())
    return SecuritySettings(**_security)


# ---------------------------------------------------------------------------
# Routes - Notifications
# ---------------------------------------------------------------------------

@router.get("/notifications", response_model=NotificationSettings)
async def get_notifications():
    """Return notification preferences."""
    return NotificationSettings(**_notifications)


@router.put("/notifications", response_model=NotificationSettings)
async def update_notifications(body: NotificationSettings):
    """Update notification preferences."""
    _notifications.update(body.model_dump())
    return NotificationSettings(**_notifications)


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
