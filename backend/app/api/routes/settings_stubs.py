"""Settings stub routes — general, security, notifications, team management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

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
# Routes — General
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
# Routes — Security
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
# Routes — Notifications
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
# Routes — Team
# ---------------------------------------------------------------------------

@router.get("/team", response_model=list[TeamMember])
async def list_team():
    """Return mock team members."""
    return [
        TeamMember(id="u-1", name="Admin User", email="admin@acme.io", role="admin", status="active", joined_at="2025-01-15T00:00:00Z"),
        TeamMember(id="u-2", name="Jane Doe", email="jdoe@acme.io", role="editor", status="active", joined_at="2025-03-10T00:00:00Z"),
        TeamMember(id="u-3", name="Ming Chen", email="mchen@acme.io", role="viewer", status="active", joined_at="2025-06-01T00:00:00Z"),
    ]
