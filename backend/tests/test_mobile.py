"""Tests for Mobile Operator App backend — services, sync, push, field annotation, biometric."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.event import Event
from app.models.integration import FieldLocation
from app.services.mobile.biometric_auth import BiometricAuthService
from app.services.mobile.field_annotation import FieldAnnotationService
from app.services.mobile.mobile_api import MobileAPIService
from app.services.mobile.offline_sync import OfflineSyncService
from app.services.mobile.push_notifications import PushNotificationService
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _make_alert(**overrides) -> Alert:
    defaults = {
        "id": uuid.uuid4(),
        "rule_id": uuid.uuid4(),
        "severity": AlertSeverity.high,
        "payload": {"message": "Intrusion detected"},
        "status": AlertStatus.new,
        "acknowledged_by": None,
        "workspace_id": WORKSPACE_ID,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    alert = MagicMock(spec=Alert)
    for k, v in defaults.items():
        setattr(alert, k, v)
    return alert


def _make_event(**overrides) -> Event:
    defaults = {
        "id": uuid.uuid4(),
        "type": "field_note",
        "payload": {"content": "All clear"},
        "timestamp": datetime.now(timezone.utc),
        "source": "mobile_app",
        "workspace_id": WORKSPACE_ID,
        "linked_asset_ids": None,
    }
    defaults.update(overrides)
    event = MagicMock(spec=Event)
    for k, v in defaults.items():
        setattr(event, k, v)
    return event


def _mock_db_session():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _scalars_result(items):
    """Return a mock execute() result whose .scalars().all() gives *items*."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = items
    result = MagicMock()
    result.scalars.return_value = scalars_mock
    return result


def _scalar_result(value):
    """Return a mock execute() result whose .scalar() gives *value*."""
    result = MagicMock()
    result.scalar.return_value = value
    result.scalar_one_or_none.return_value = value
    return result


# ---------------------------------------------------------------------------
# Mobile dashboard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mobile_dashboard_compact():
    """Dashboard returns compact payload with expected keys."""
    alerts = [_make_alert() for _ in range(3)]
    events = [_make_event() for _ in range(2)]
    db = _mock_db_session()

    # Four queries: alerts, pending count, notifications
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result(alerts),    # top 10 alerts
            _scalar_result(5),          # pending reviews count
            _scalars_result(events),    # notifications
        ]
    )

    result = await MobileAPIService.get_mobile_dashboard(db, WORKSPACE_ID, USER_ID)

    assert "alerts" in result
    assert len(result["alerts"]) == 3
    assert result["pending_reviews"] == 5
    assert "active_streams" in result
    assert "my_shifts" in result
    assert "notifications" in result
    assert len(result["notifications"]) == 2


# ---------------------------------------------------------------------------
# Mobile alerts (paginated)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mobile_alerts_paginated():
    """Alert list returns compact items."""
    alerts = [_make_alert() for _ in range(5)]
    db = _mock_db_session()
    db.execute = AsyncMock(return_value=_scalars_result(alerts))

    result = await MobileAPIService.get_mobile_alerts(db, WORKSPACE_ID, limit=5, offset=0)

    assert len(result) == 5
    assert "id" in result[0]
    assert "severity" in result[0]
    assert "thumbnail" in result[0]


# ---------------------------------------------------------------------------
# Acknowledge with location
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acknowledge_with_location():
    """Acknowledging an alert records GPS location."""
    alert = _make_alert()
    db = _mock_db_session()
    db.execute = AsyncMock(return_value=_scalar_result(alert))

    location = {"latitude": 40.7128, "longitude": -74.0060, "accuracy_m": 5.0}
    result = await MobileAPIService.acknowledge_mobile(
        db, alert.id, USER_ID, location=location,
    )

    assert result["acknowledged"] is True
    assert alert.status == AlertStatus.acknowledged
    assert alert.acknowledged_by == USER_ID


# ---------------------------------------------------------------------------
# Field evidence upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_evidence_upload():
    """Evidence upload returns asset_id and uploaded=True."""
    db = _mock_db_session()
    file_bytes = b"fake-image-data-12345"
    metadata = {"filename": "evidence.jpg", "content_type": "image/jpeg"}

    result = await MobileAPIService.upload_field_evidence(
        db, WORKSPACE_ID, USER_ID, file_bytes, metadata,
    )

    assert result["uploaded"] is True
    assert "asset_id" in result
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Offline package
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_offline_package_generation():
    """Offline package contains alerts, cases, contacts, and last_sync."""
    alerts = [_make_alert() for _ in range(2)]
    cases = [_make_event(type="case") for _ in range(1)]
    db = _mock_db_session()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result(alerts),
            _scalars_result(cases),
        ]
    )

    result = await MobileAPIService.get_offline_package(db, WORKSPACE_ID)

    assert "alerts" in result
    assert "cases" in result
    assert "contacts" in result
    assert "offline_model_url" in result
    assert "last_sync" in result


# ---------------------------------------------------------------------------
# Offline sync processing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_offline_sync_processing():
    """Offline actions are processed; conflicts detected for resolved alerts."""
    alert_new = _make_alert(status=AlertStatus.new)
    alert_resolved = _make_alert(status=AlertStatus.resolved)

    db = _mock_db_session()

    # First action finds new alert, second finds resolved alert
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(alert_new),
            _scalar_result(alert_resolved),
        ]
    )

    actions = [
        {"type": "acknowledge_alert", "alert_id": str(alert_new.id), "user_id": str(USER_ID)},
        {"type": "acknowledge_alert", "alert_id": str(alert_resolved.id), "user_id": str(USER_ID)},
    ]

    result = await OfflineSyncService.process_offline_actions(db, actions)

    assert result["processed"] == 1
    assert len(result["conflicts"]) == 1
    assert "already resolved" in result["conflicts"][0]["reason"]


# ---------------------------------------------------------------------------
# Push notification stub
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_notification_stub():
    """Push stub returns sent=False with stub method."""
    result = await PushNotificationService.send_push(
        "device-token-abc", "Test", "Hello world",
    )
    assert result["sent"] is False
    assert result["method"] == "stub"
    assert "FIREBASE_SERVER_KEY" in result["note"]


# ---------------------------------------------------------------------------
# Push preferences
# ---------------------------------------------------------------------------


@pytest.fixture
async def mobile_db():
    """A real session — push registrations and preferences are rows now."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_push_preferences(mobile_db):
    """Preferences default sensibly, then round-trip through the database."""
    user_id = uuid.uuid4()

    prefs = await PushNotificationService.notification_preferences(mobile_db, user_id)
    assert prefs["alerts_enabled"] is True

    updated = await PushNotificationService.update_preferences(
        mobile_db, user_id, {"alerts_enabled": False, "sound": False},
    )
    assert updated["alerts_enabled"] is False
    assert updated["sound"] is False

    # Unspecified keys keep their defaults.
    assert updated["severity_filter"] == "all"

    again = await PushNotificationService.notification_preferences(mobile_db, user_id)
    assert again["alerts_enabled"] is False


@pytest.mark.asyncio
async def test_device_registration_round_trip(mobile_db):
    """A registered device is listed, deduplicated, and can be removed."""
    user_id = uuid.uuid4()

    await PushNotificationService.register_device(
        mobile_db, user_id, "token-abc", "ios",
    )
    # Registering the same token again must not create a duplicate the same
    # push would be delivered to twice.
    await PushNotificationService.register_device(
        mobile_db, user_id, "token-abc", "android",
    )

    devices = await PushNotificationService.list_devices(mobile_db, user_id)
    assert devices == [{"token": "token-abc", "platform": "android"}]

    sent = await PushNotificationService.send_to_user(
        mobile_db, user_id, "Title", "Body",
    )
    assert sent["devices_notified"] == 1

    assert (
        await PushNotificationService.unregister_device(
            mobile_db, user_id, "token-abc"
        )
    )["unregistered"] is True
    assert await PushNotificationService.list_devices(mobile_db, user_id) == []


@pytest.mark.asyncio
async def test_push_registrations_survive_a_restart():
    """Registrations and preferences outlive the process that made them."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)
    user_id = uuid.uuid4()

    try:
        async with factory() as session:
            await PushNotificationService.register_device(
                session, user_id, "durable-token", "ios",
            )
            await PushNotificationService.update_preferences(
                session, user_id, {"sound": False},
            )
    finally:
        await engine.dispose()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            devices = await PushNotificationService.list_devices(session, user_id)
            assert [d["token"] for d in devices] == ["durable-token"]

            prefs = await PushNotificationService.notification_preferences(
                session, user_id
            )
            assert prefs["sound"] is False
    finally:
        await restarted_engine.dispose()


# ---------------------------------------------------------------------------
# Field note with GPS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_note_with_gps():
    """Field note creation includes GPS location in payload."""
    db = _mock_db_session()

    # Mock the refreshed event
    mock_event = _make_event(type="field_note")
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    # Patch the Event constructor result indirectly via commit
    result = await FieldAnnotationService.create_field_note(
        db,
        WORKSPACE_ID,
        USER_ID,
        "Perimeter check complete",
        location={"latitude": 51.5074, "longitude": -0.1278, "accuracy_m": 3.0},
    )

    db.commit.assert_awaited_once()

    # Two rows are staged: the note itself and the operator's position, which
    # is now recorded in field_locations rather than a module dict.
    added = [call.args[0] for call in db.add.call_args_list]
    assert len(added) == 2

    added_event = next(obj for obj in added if getattr(obj, "type", None) == "field_note")
    assert added_event.payload["location"]["latitude"] == 51.5074

    location_row = next(obj for obj in added if isinstance(obj, FieldLocation))
    assert location_row.latitude == 51.5074
    assert location_row.user_ref == str(USER_ID)


# ---------------------------------------------------------------------------
# Field photo creates asset
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_field_photo_creates_asset():
    """Field photo creates an event with asset reference."""
    db = _mock_db_session()
    photo_bytes = b"\x89PNG\r\n\x1a\nfake-png-data"

    result = await FieldAnnotationService.create_field_photo(
        db, WORKSPACE_ID, USER_ID, photo_bytes, "Suspicious vehicle",
    )

    assert "asset_id" in result
    assert "event_id" in result
    assert result["size_bytes"] == len(photo_bytes)
    db.add.assert_called_once()

    added_event = db.add.call_args[0][0]
    assert added_event.type == "field_photo"
    assert added_event.payload["notes"] == "Suspicious vehicle"


# ---------------------------------------------------------------------------
# Biometric auth stub
# ---------------------------------------------------------------------------


def test_biometric_stub():
    """Biometric registration returns stub note."""
    result = BiometricAuthService.register_biometric_stub("user-123", "face_id")
    assert result["registered"] is True
    assert "mobile OS" in result["note"]


def test_biometric_verify_invalid():
    """Invalid token returns valid=False."""
    result = BiometricAuthService.verify_biometric_token("invalid.jwt.token")
    assert result["valid"] is False
    assert result["user_id"] is None


# ---------------------------------------------------------------------------
# API route tests (via FastAPI TestClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_dashboard_reports_measured_counts_only():
    """GET /api/mobile/dashboard counts field notes and admits what it cannot measure.

    This replaces a test that patched `routes.mobile.MobileAPIService`, which
    the route does not use, and asserted a shape it no longer returns: stream,
    alert and review counts used to be the hard-coded numbers 3, 2 and 5, and
    are now reported as unmeasured rather than invented.
    """
    from httpx import ASGITransport, AsyncClient

    from app.database import get_async_session
    from app.main import app
    from app.models.field_note import FieldNote
    from tests.db_utils import (
        db_session_factory,
        fresh_engine,
        requires_postgres,
        seed_workspace,
    )

    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)
    async with factory() as session:
        workspace_id = await seed_workspace(session, "mobile-dashboard")
        session.add(
            FieldNote(
                workspace_id=workspace_id,
                title="Gate B check",
                content="Nothing unusual.",
            )
        )
        await session.commit()

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/mobile/dashboard", params={"workspace_id": str(workspace_id)}
            )
    finally:
        app.dependency_overrides.pop(get_async_session, None)
        await engine.dispose()

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["field_notes"] == 1
    for key in ("active_streams", "recent_alerts", "pending_reviews"):
        assert data[key] is None, f"{key} should be reported as unmeasured, not guessed"
        assert key in data["unmeasured"]


@pytest.mark.asyncio
async def test_api_sync_replays_offline_actions():
    """POST /api/mobile/sync replays a queued action against the database.

    The endpoint did not exist: OfflineSyncService could replay offline
    actions, but nothing exposed it, so a mobile client had no way to sync.
    """
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import func, select

    from app.database import get_async_session
    from app.main import app
    from app.models.field_note import FieldNote
    from tests.db_utils import (
        db_session_factory,
        fresh_engine,
        requires_postgres,
        seed_workspace,
    )

    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)
    async with factory() as session:
        workspace_id = await seed_workspace(session, "mobile-sync")

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/mobile/sync",
                json={
                    "actions": [
                        {
                            "type": "add_note",
                            "workspace_id": str(workspace_id),
                            "title": "Queued while offline",
                            "content": "Recorded at the perimeter.",
                        }
                    ]
                },
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["processed"] == 1
        assert body["failed"] == 0

        # The action must have actually landed, not merely been counted.
        async with factory() as session:
            stored = (
                await session.execute(
                    select(func.count())
                    .select_from(FieldNote)
                    .where(FieldNote.workspace_id == workspace_id)
                )
            ).scalar()
        assert stored == 1
    finally:
        app.dependency_overrides.pop(get_async_session, None)
        await engine.dispose()
