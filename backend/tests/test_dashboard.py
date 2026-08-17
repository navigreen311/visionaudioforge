"""Tests for the dashboard — the first screen anyone sees.

These run against a real database so the aggregate queries are actually
executed; they skip when no server is reachable (as in CI).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_db
from app.main import app
from app.models.alert import Alert, AlertRule, AlertSeverity, AlertStatus
from app.models.asset import Asset, AssetType
from app.models.command_center import CommandStream, StreamSourceType, StreamStatus
from app.models.model_registry import ModelRecord
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_env():
    """Yield (session_factory, workspace_id) against a real database."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "dashboard")

    try:
        yield factory, workspace_id
    finally:
        await engine.dispose()


@pytest.fixture
async def client(db_env):
    """HTTP client whose requests use the test database session."""
    factory, _ = db_env

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Fixtures for populating each counted source
# ---------------------------------------------------------------------------

async def _seed_dashboard_data(factory, workspace_id) -> None:
    """Insert one of everything the dashboard counts."""
    async with factory() as session:
        session.add(
            CommandStream(
                id=uuid4(),
                workspace_id=workspace_id,
                name="lobby-cam",
                source_type=StreamSourceType.rtsp,
                status=StreamStatus.connected,
                position=0,
            )
        )
        session.add(
            CommandStream(
                id=uuid4(),
                workspace_id=workspace_id,
                name="dock-cam",
                source_type=StreamSourceType.rtsp,
                status=StreamStatus.disconnected,
                position=1,
            )
        )
        session.add(
            ModelRecord(
                id=uuid4(),
                workspace_id=workspace_id,
                name="detector",
                version="1.0",
                status="production",
            )
        )
        session.add(
            ModelRecord(
                id=uuid4(),
                workspace_id=workspace_id,
                name="draft-detector",
                version="0.1",
                status="registered",
            )
        )
        session.add(
            Asset(
                id=uuid4(),
                workspace_id=workspace_id,
                type=AssetType.image,
                path="/data/a.png",
                filename="a.png",
            )
        )

        rule = AlertRule(
            id=uuid4(),
            workspace_id=workspace_id,
            name="perimeter",
            conditions={},
            actions={},
        )
        session.add(rule)
        await session.flush()

        session.add(
            Alert(
                id=uuid4(),
                workspace_id=workspace_id,
                rule_id=rule.id,
                severity=AlertSeverity.critical,
                status=AlertStatus.new,
                payload={"message": "Perimeter breach at east gate"},
            )
        )
        session.add(
            Alert(
                id=uuid4(),
                workspace_id=workspace_id,
                rule_id=rule.id,
                severity=AlertSeverity.low,
                status=AlertStatus.resolved,
                payload={},
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_stats_counts_are_real(db_env, client):
    """Every stat reflects rows in the database, not a hardcoded zero."""
    factory, workspace_id = db_env
    await _seed_dashboard_data(factory, workspace_id)

    resp = await client.get(f"/api/dashboard/stats?range=7d&workspace_id={workspace_id}")
    assert resp.status_code == 200
    data = resp.json()

    # Only the connected stream counts as active.
    assert data["active_streams"] == 1
    # Only the "production" model counts as in production.
    assert data["models_production"] == 1
    # New and acknowledged alerts are open; resolved is not.
    assert data["open_alerts"] == 1
    assert data["total_assets"] == 1


@pytest.mark.anyio
async def test_stats_are_workspace_scoped(db_env, client):
    """A second workspace's rows must not leak into the first one's counts."""
    factory, workspace_id = db_env
    await _seed_dashboard_data(factory, workspace_id)

    async with factory() as session:
        other_id = await seed_workspace(session, "other")
    await _seed_dashboard_data(factory, other_id)

    resp = await client.get(f"/api/dashboard/stats?workspace_id={workspace_id}")
    assert resp.json()["total_assets"] == 1

    both = await client.get("/api/dashboard/stats")
    assert both.json()["total_assets"] >= 2


@pytest.mark.anyio
@pytest.mark.parametrize("range_key,expected", [("7d", 7), ("14d", 14), ("30d", 30)])
async def test_history_length_matches_range(db_env, client, range_key, expected):
    """Sparklines must have one bucket per day in the requested range."""
    factory, workspace_id = db_env

    resp = await client.get(
        f"/api/dashboard/stats?range={range_key}&workspace_id={workspace_id}"
    )
    data = resp.json()

    for key in ("streams_history", "models_history", "alerts_history", "assets_history"):
        assert len(data[key]) == expected, f"{key} has the wrong bucket count"


@pytest.mark.anyio
async def test_history_buckets_todays_rows(db_env, client):
    """A row created today lands in the last bucket, not a zero-filled list."""
    factory, workspace_id = db_env
    await _seed_dashboard_data(factory, workspace_id)

    resp = await client.get(f"/api/dashboard/stats?workspace_id={workspace_id}")
    assets_history = resp.json()["assets_history"]

    assert sum(assets_history) == 1
    assert assets_history[-1] == 1


# ---------------------------------------------------------------------------
# /activity
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_activity_is_not_empty(db_env, client):
    """The feed reports real records rather than always returning []."""
    factory, workspace_id = db_env
    await _seed_dashboard_data(factory, workspace_id)

    resp = await client.get(f"/api/dashboard/activity?workspace_id={workspace_id}")
    assert resp.status_code == 200
    items = resp.json()

    assert items, "activity feed is empty despite seeded records"
    for item in items:
        assert item["type"]
        assert item["message"]
        assert item["timestamp"]


@pytest.mark.anyio
async def test_activity_covers_multiple_sources(db_env, client):
    """Alerts, uploads, models and streams all reach the feed."""
    factory, workspace_id = db_env
    await _seed_dashboard_data(factory, workspace_id)

    resp = await client.get(f"/api/dashboard/activity?workspace_id={workspace_id}&limit=100")
    types = {item["type"] for item in resp.json()}

    assert {"alert", "upload", "model", "capture"} <= types


@pytest.mark.anyio
async def test_activity_carries_alert_detail(db_env, client):
    """An alert's payload message surfaces instead of a generic label."""
    factory, workspace_id = db_env
    await _seed_dashboard_data(factory, workspace_id)

    resp = await client.get(f"/api/dashboard/activity?workspace_id={workspace_id}&limit=100")
    messages = [item["message"] for item in resp.json()]

    assert "Perimeter breach at east gate" in messages


@pytest.mark.anyio
async def test_activity_is_newest_first_and_honours_limit(db_env, client):
    """The feed is sorted newest-first and never exceeds the requested limit."""
    factory, workspace_id = db_env
    await _seed_dashboard_data(factory, workspace_id)

    resp = await client.get(f"/api/dashboard/activity?workspace_id={workspace_id}&limit=3")
    items = resp.json()

    assert len(items) <= 3
    timestamps = [item["timestamp"] for item in items]
    assert timestamps == sorted(timestamps, reverse=True)


@pytest.mark.anyio
async def test_activity_is_workspace_scoped(db_env, client):
    """One workspace's activity must not appear in another's feed."""
    factory, workspace_id = db_env

    async with factory() as session:
        other_id = await seed_workspace(session, "other-activity")
    await _seed_dashboard_data(factory, other_id)

    resp = await client.get(f"/api/dashboard/activity?workspace_id={workspace_id}")
    assert resp.json() == []
