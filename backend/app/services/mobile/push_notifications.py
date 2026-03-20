"""Push notification service — device registration, sending, and preferences.

V1 is a stub: notifications are logged but not delivered via FCM/APNs.
Set FIREBASE_SERVER_KEY in environment to enable real push delivery.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event

logger = logging.getLogger(__name__)

# In-memory stores (replace with DB tables in production)
_device_registry: dict[str, list[dict[str, str]]] = {}  # user_id -> [{token, platform}]
_user_preferences: dict[str, dict[str, Any]] = {}  # user_id -> prefs


class PushNotificationService:
    """Push notification management for mobile operator app."""

    # ------------------------------------------------------------------
    # Device registration
    # ------------------------------------------------------------------

    @staticmethod
    async def register_device(
        db: AsyncSession,
        user_id: uuid.UUID,
        device_token: str,
        platform: str,
    ) -> dict[str, Any]:
        """Register a device for push notifications.

        Args:
            platform: 'ios', 'android', or 'web'
        """
        uid = str(user_id)
        if uid not in _device_registry:
            _device_registry[uid] = []

        # Avoid duplicate tokens
        existing_tokens = {d["token"] for d in _device_registry[uid]}
        if device_token not in existing_tokens:
            _device_registry[uid].append({"token": device_token, "platform": platform})

        logger.info("Device registered for user %s (%s)", user_id, platform)
        return {"registered": True}

    # ------------------------------------------------------------------
    # Send push (stub)
    # ------------------------------------------------------------------

    @staticmethod
    async def send_push(
        device_token: str,
        title: str,
        body: str,
        data: Optional[dict] = None,
        platform: str = "ios",
    ) -> dict[str, Any]:
        """Send a push notification to a single device.

        V1 stub: logs the notification. Real push requires FCM setup.
        """
        logger.info(
            "PUSH STUB [%s] token=%s title=%r body=%r data=%s",
            platform,
            device_token[:12] + "...",
            title,
            body[:80],
            data,
        )
        return {
            "sent": False,
            "method": "stub",
            "note": "Set FIREBASE_SERVER_KEY for real push notifications",
        }

    # ------------------------------------------------------------------
    # Send to user (all devices)
    # ------------------------------------------------------------------

    @staticmethod
    async def send_to_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        body: str,
        data: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Send a push notification to all of a user's registered devices."""
        uid = str(user_id)
        devices = _device_registry.get(uid, [])
        for device in devices:
            await PushNotificationService.send_push(
                device["token"], title, body, data=data, platform=device["platform"],
            )
        return {"devices_notified": len(devices)}

    # ------------------------------------------------------------------
    # Broadcast to workspace
    # ------------------------------------------------------------------

    @staticmethod
    async def send_to_workspace(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        title: str,
        body: str,
        data: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Broadcast a push notification to all workspace members."""
        from app.models.user import User

        stmt = select(User.id).where(User.workspace_id == workspace_id)
        result = await db.execute(stmt)
        user_ids = [row[0] for row in result.all()]

        total_notified = 0
        for uid in user_ids:
            resp = await PushNotificationService.send_to_user(db, uid, title, body, data=data)
            total_notified += resp["devices_notified"]

        return {"users_notified": len(user_ids)}

    # ------------------------------------------------------------------
    # Alert-specific notification
    # ------------------------------------------------------------------

    @staticmethod
    async def send_alert_notification(
        db: AsyncSession,
        alert: Any,
    ) -> dict[str, Any]:
        """Notify relevant operators about an alert based on workspace membership."""
        severity = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        title = f"Alert: {severity.upper()}"
        body_text = ""
        if alert.payload and isinstance(alert.payload, dict):
            body_text = alert.payload.get("message", f"{severity} alert triggered")[:200]
        else:
            body_text = f"{severity} alert triggered"

        return await PushNotificationService.send_to_workspace(
            db,
            alert.workspace_id,
            title,
            body_text,
            data={"alert_id": str(alert.id), "severity": severity},
        )

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    @staticmethod
    async def notification_preferences(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get push notification preferences for a user."""
        uid = str(user_id)
        defaults = {
            "alerts_enabled": True,
            "severity_filter": "all",
            "quiet_hours": {"enabled": False, "start": "22:00", "end": "07:00"},
            "sound": True,
        }
        return _user_preferences.get(uid, defaults)

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        user_id: uuid.UUID,
        prefs: dict[str, Any],
    ) -> dict[str, Any]:
        """Update push notification preferences for a user."""
        uid = str(user_id)
        current = await PushNotificationService.notification_preferences(db, user_id)
        current.update(prefs)
        _user_preferences[uid] = current
        logger.info("Updated push preferences for user %s", user_id)
        return current
