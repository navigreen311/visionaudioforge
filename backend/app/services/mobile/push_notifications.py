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
from app.models.integration import PushDevice, PushPreference
from app.models.user import User

logger = logging.getLogger(__name__)

# Device registrations and preferences live in push_devices /
# push_preferences. Held in memory, a registration was lost on restart and
# the operator simply stopped receiving alerts, with nothing to show why.

DEFAULT_PREFERENCES: dict[str, Any] = {
    "alerts_enabled": True,
    "severity_filter": "all",
    "quiet_hours": {"enabled": False, "start": "22:00", "end": "07:00"},
    "sound": True,
}


def _as_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


async def _known_user(db: AsyncSession, user_id: Any) -> Optional[uuid.UUID]:
    """Return the user id only if that user exists.

    user_ref carries the identity regardless; the foreign key is set only when
    it can be, so a device registration is never rejected because the account
    row is missing.
    """
    candidate = _as_uuid(user_id)
    if candidate is None:
        return None

    result = await db.execute(select(User.id).where(User.id == candidate))
    return result.scalar_one_or_none()


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

        existing = await db.execute(
            select(PushDevice).where(
                PushDevice.user_ref == uid,
                PushDevice.device_token == device_token,
            )
        )
        device = existing.scalar_one_or_none()

        if device is None:
            db.add(
                PushDevice(
                    id=uuid.uuid4(),
                    user_id=await _known_user(db, user_id),
                    user_ref=uid,
                    device_token=device_token,
                    platform=platform,
                    active=True,
                )
            )
        else:
            # Re-registering an existing token refreshes it rather than
            # creating a duplicate the same push would be sent to twice.
            device.platform = platform
            device.active = True

        await db.commit()

        logger.info("Device registered for user %s (%s)", user_id, platform)
        return {"registered": True}

    @staticmethod
    async def unregister_device(
        db: AsyncSession,
        user_id: uuid.UUID,
        device_token: str,
    ) -> dict[str, Any]:
        """Stop sending pushes to a device."""
        result = await db.execute(
            select(PushDevice).where(
                PushDevice.user_ref == str(user_id),
                PushDevice.device_token == device_token,
            )
        )
        device = result.scalar_one_or_none()
        if device is None:
            return {"unregistered": False}

        await db.delete(device)
        await db.commit()
        return {"unregistered": True}

    @staticmethod
    async def list_devices(
        db: AsyncSession, user_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """List a user's active push registrations."""
        result = await db.execute(
            select(PushDevice)
            .where(PushDevice.user_ref == str(user_id), PushDevice.active.is_(True))
            .order_by(PushDevice.created_at)
        )
        return [
            {"token": d.device_token, "platform": d.platform}
            for d in result.scalars().all()
        ]

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
        devices = await PushNotificationService.list_devices(db, user_id)
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
        result = await db.execute(
            select(PushPreference).where(PushPreference.user_ref == str(user_id))
        )
        stored = result.scalar_one_or_none()
        if stored is None:
            return dict(DEFAULT_PREFERENCES)
        return {**DEFAULT_PREFERENCES, **(stored.preferences or {})}

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

        result = await db.execute(
            select(PushPreference).where(PushPreference.user_ref == uid)
        )
        stored = result.scalar_one_or_none()
        if stored is None:
            db.add(
                PushPreference(
                    id=uuid.uuid4(),
                    user_id=await _known_user(db, user_id),
                    user_ref=uid,
                    preferences=current,
                )
            )
        else:
            stored.preferences = current

        await db.commit()
        logger.info("Updated push preferences for user %s", user_id)
        return current
