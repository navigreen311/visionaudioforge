"""Settings API stubs — notification preferences and integration status."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Notification schemas
# ---------------------------------------------------------------------------

class NotificationChannel(BaseModel):
    inApp: bool = False
    email: bool = False
    slack: bool = False


class NotificationEvent(BaseModel):
    key: str
    label: str
    channels: NotificationChannel


class NotificationCategory(BaseModel):
    key: str
    label: str
    events: list[NotificationEvent]


class NotificationPreferences(BaseModel):
    categories: list[NotificationCategory] = []


class IntegrationStatus(BaseModel):
    slack: bool = False
    email: bool = False
    webhook: bool = False


# ---------------------------------------------------------------------------
# In-memory store (replace with DB in production)
# ---------------------------------------------------------------------------

_notification_prefs: NotificationPreferences | None = None

_DEFAULT_NOTIFICATION_CATEGORIES: list[dict[str, object]] = [
    {
        "key": "alerts",
        "label": "Alerts",
        "events": [
            {"key": "alert_critical", "label": "Critical alert triggered", "channels": {"inApp": True, "email": True, "slack": False}},
            {"key": "alert_warning", "label": "Warning alert triggered", "channels": {"inApp": True, "email": False, "slack": False}},
            {"key": "alert_acknowledged", "label": "Alert acknowledged", "channels": {"inApp": True, "email": False, "slack": False}},
        ],
    },
    {
        "key": "pipeline",
        "label": "Pipeline",
        "events": [
            {"key": "pipeline_completed", "label": "Pipeline completed", "channels": {"inApp": True, "email": False, "slack": False}},
            {"key": "pipeline_failed", "label": "Pipeline failed", "channels": {"inApp": True, "email": True, "slack": False}},
            {"key": "pipeline_scheduled", "label": "Pipeline scheduled", "channels": {"inApp": False, "email": False, "slack": False}},
        ],
    },
    {
        "key": "models",
        "label": "Models",
        "events": [
            {"key": "model_training_completed", "label": "Training completed", "channels": {"inApp": True, "email": False, "slack": False}},
            {"key": "model_deployed", "label": "Model deployed", "channels": {"inApp": True, "email": True, "slack": False}},
        ],
    },
    {
        "key": "system",
        "label": "System",
        "events": [
            {"key": "system_weekly_digest", "label": "Weekly digest", "channels": {"inApp": False, "email": True, "slack": False}},
            {"key": "system_sla_violation", "label": "SLA violation", "channels": {"inApp": True, "email": True, "slack": False}},
            {"key": "system_storage_threshold", "label": "Storage usage > 80%", "channels": {"inApp": True, "email": True, "slack": False}},
        ],
    },
]


# ---------------------------------------------------------------------------
# Notification routes
# ---------------------------------------------------------------------------

@router.get("/notifications", response_model=NotificationPreferences)
async def get_notification_preferences():
    """Return saved notification preferences or defaults."""
    if _notification_prefs is not None:
        return _notification_prefs
    return NotificationPreferences(
        categories=[NotificationCategory(**cat) for cat in _DEFAULT_NOTIFICATION_CATEGORIES],  # type: ignore[arg-type]
    )


@router.put("/notifications", response_model=NotificationPreferences)
async def update_notification_preferences(body: NotificationPreferences):
    """Save notification preferences."""
    global _notification_prefs  # noqa: PLW0603
    _notification_prefs = body
    return _notification_prefs


@router.get("/integrations", response_model=IntegrationStatus)
async def get_integration_status():
    """Return which integrations are currently connected."""
    return IntegrationStatus(slack=False, email=False, webhook=False)
