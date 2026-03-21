"""Settings API routes — integrations config, billing, notifications, security."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ── Pydantic models ─────────────────────────────────────────────────


class IntegrationConfig(BaseModel):
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class NotificationPreferences(BaseModel):
    email_alerts: bool = True
    slack_alerts: bool = False
    in_app: bool = True
    digest_frequency: str = Field("daily", examples=["realtime", "daily", "weekly"])
    categories: dict[str, bool] = Field(
        default_factory=lambda: {
            "system": True,
            "security": True,
            "billing": True,
            "pipeline": True,
            "team": True,
        }
    )


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


# ── In-memory state (stub) ──────────────────────────────────────────

_integrations: dict[str, dict[str, Any]] = {
    "slack": {
        "type": "slack",
        "name": "Slack",
        "description": "Send alerts and reports to Slack channels",
        "connected": False,
        "config": {},
    },
    "email": {
        "type": "email",
        "name": "Email",
        "description": "Email notifications via SMTP or SendGrid",
        "connected": True,
        "config": {"smtp_host": "smtp.example.com", "from": "noreply@example.com"},
    },
    "webhook": {
        "type": "webhook",
        "name": "Webhook",
        "description": "Outbound webhooks for pipeline events",
        "connected": False,
        "config": {},
    },
    "s3": {
        "type": "s3",
        "name": "Amazon S3",
        "description": "Cloud storage for assets and exports",
        "connected": True,
        "config": {"bucket": "my-bucket", "region": "us-east-1"},
    },
}

_notification_prefs = NotificationPreferences()

_sessions = [
    {
        "id": "sess-1",
        "device": "Chrome on Windows",
        "ip": "192.168.1.10",
        "location": "New York, US",
        "last_active": "2026-03-21T10:30:00Z",
        "current": True,
    },
    {
        "id": "sess-2",
        "device": "Safari on macOS",
        "ip": "10.0.0.42",
        "location": "San Francisco, US",
        "last_active": "2026-03-20T18:15:00Z",
        "current": False,
    },
    {
        "id": "sess-3",
        "device": "Mobile App (iOS)",
        "ip": "172.16.0.5",
        "location": "Chicago, US",
        "last_active": "2026-03-19T09:00:00Z",
        "current": False,
    },
]

_VALID_TYPES = {"slack", "email", "webhook", "s3"}


# ── Integrations ────────────────────────────────────────────────────


@router.get("/integrations")
async def list_integrations() -> list[dict[str, Any]]:
    """Return all available integrations with their connected status."""
    return list(_integrations.values())


@router.post("/integrations/{integration_type}")
async def save_integration_config(
    integration_type: str, body: IntegrationConfig
) -> dict[str, Any]:
    """Save configuration for an integration type."""
    if integration_type not in _VALID_TYPES:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {integration_type}")
    _integrations[integration_type]["connected"] = body.enabled
    _integrations[integration_type]["config"] = body.config
    return {"success": True, "integration": _integrations[integration_type]}


@router.post("/integrations/{integration_type}/test")
async def test_integration(integration_type: str) -> dict[str, Any]:
    """Run a connectivity test for the given integration."""
    if integration_type not in _VALID_TYPES:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {integration_type}")
    return {"success": True, "message": "Test sent"}


# ── Billing ─────────────────────────────────────────────────────────


@router.get("/billing")
async def get_billing() -> dict[str, Any]:
    """Return current plan, usage meters, and billing history."""
    return {
        "plan": "free",
        "usage": {
            "api_calls": {"used": 1_234, "limit": 10_000, "unit": "requests/month"},
            "storage": {"used": 256, "limit": 5_000, "unit": "MB"},
            "pipelines": {"used": 3, "limit": 5, "unit": "active"},
            "team_members": {"used": 2, "limit": 3, "unit": "seats"},
        },
        "billing_history": [],
    }


# ── Notifications ───────────────────────────────────────────────────


@router.get("/notifications")
async def get_notification_preferences() -> dict[str, Any]:
    """Return the notification preferences grid."""
    global _notification_prefs
    return {
        "email_alerts": _notification_prefs.email_alerts,
        "slack_alerts": _notification_prefs.slack_alerts,
        "in_app": _notification_prefs.in_app,
        "digest_frequency": _notification_prefs.digest_frequency,
        "categories": _notification_prefs.categories,
    }


@router.put("/notifications")
async def update_notification_preferences(body: NotificationPreferences) -> dict[str, Any]:
    """Save notification preferences."""
    global _notification_prefs
    _notification_prefs = body
    return {"success": True, "preferences": body.model_dump()}


# ── Security ────────────────────────────────────────────────────────


@router.get("/security/sessions")
async def list_sessions() -> list[dict[str, Any]]:
    """Return active sessions."""
    return _sessions


@router.delete("/security/sessions/{session_id}")
async def revoke_session(session_id: str) -> dict[str, Any]:
    """Revoke (delete) a session by ID."""
    global _sessions
    before = len(_sessions)
    _sessions = [s for s in _sessions if s["id"] != session_id]
    if len(_sessions) == before:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": f"Session {session_id} revoked"}


@router.post("/security/2fa/enable")
async def enable_2fa() -> dict[str, Any]:
    """Enable two-factor authentication (stub)."""
    return {"enabled": True, "method": "totp", "provisioned_at": datetime.now(timezone.utc).isoformat()}


@router.post("/security/password")
async def change_password(body: PasswordChangeRequest) -> dict[str, Any]:
    """Change the current user's password (stub)."""
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    return {"success": True, "message": "Password updated successfully"}
