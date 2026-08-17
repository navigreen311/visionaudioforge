"""Command Center API tests against a real database.

The unit tests in test_command_center.py exercise the service layer with mocked
sessions. These drive the HTTP routes against Postgres, so the mapping between
stored state and the console's contract is covered, along with the durability
the move off module-level dicts was for.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_db
from app.main import app
from app.models.command_center import Incident, IncidentSeverity, IncidentStatus
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from tests.db_utils import db_session_factory, fresh_engine, requires_postgres


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def cc_env():
    """Yield (session_factory, workspace_id) with an owner already in place.

    Shifts reference an operator, so the workspace needs an owner for the
    console's operator-less Start Shift call to resolve.
    """
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    workspace_id = uuid.uuid4()
    async with factory() as session:
        owner = User(
            id=uuid.uuid4(),
            email=f"operator-{uuid.uuid4().hex[:8]}@example.test",
            hashed_password="x",
            role=UserRole.operator,
        )
        session.add(owner)
        await session.flush()

        session.add(
            Workspace(
                id=workspace_id,
                name="cockpit",
                slug=f"cockpit-{uuid.uuid4().hex[:8]}",
                owner_id=owner.id,
            )
        )
        await session.commit()

    try:
        yield factory, workspace_id
    finally:
        await engine.dispose()


@pytest.fixture
async def client(cc_env):
    factory, _ = cc_env

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


@pytest.fixture
def workspace_id(cc_env):
    return str(cc_env[1])


async def _add_stream(client, workspace_id, name="lobby-cam", source_type="rtsp"):
    resp = await client.post(
        f"/api/command-center/streams?workspace_id={workspace_id}",
        json={"name": name, "source_type": source_type, "url": "rtsp://host/1"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _seed_incident(factory, workspace_id, title="Perimeter breach"):
    incident_id = uuid.uuid4()
    async with factory() as session:
        session.add(
            Incident(
                id=incident_id,
                workspace_id=uuid.UUID(workspace_id),
                title=title,
                description="Motion after hours",
                severity=IncidentSeverity.critical,
                status=IncidentStatus.active,
            )
        )
        await session.commit()
    return str(incident_id)


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_add_stream_returns_console_shape(client, workspace_id):
    """The response carries every field the console's Stream type reads."""
    stream = await _add_stream(client, workspace_id)

    assert stream["id"]
    assert stream["name"] == "lobby-cam"
    assert stream["source_type"] == "rtsp"
    assert stream["url"] == "rtsp://host/1"
    assert stream["status"] == "online"
    assert stream["position"] == 0
    assert stream["is_primary"] is False
    assert stream["created_at"]


@pytest.mark.anyio
@pytest.mark.parametrize("source_type", ["camera", "rtsp", "screen"])
async def test_console_source_types_are_accepted(client, workspace_id, source_type):
    """camera and screen are what the Add Stream dialog offers alongside rtsp."""
    stream = await _add_stream(client, workspace_id, f"cam-{source_type}", source_type)
    assert stream["source_type"] == source_type


@pytest.mark.anyio
async def test_list_streams_is_ordered_and_scoped(client, workspace_id, cc_env):
    """Streams come back in wall order, and only this workspace's."""
    await _add_stream(client, workspace_id, "first")
    await _add_stream(client, workspace_id, "second")

    resp = await client.get(f"/api/command-center/streams?workspace_id={workspace_id}")
    assert resp.status_code == 200
    assert [s["name"] for s in resp.json()] == ["first", "second"]

    other = uuid.uuid4()
    factory, _ = cc_env
    async with factory() as session:
        session.add(
            Workspace(id=other, name="other", slug=f"other-{uuid.uuid4().hex[:8]}")
        )
        await session.commit()

    other_resp = await client.get(f"/api/command-center/streams?workspace_id={other}")
    assert other_resp.json() == []


@pytest.mark.anyio
async def test_stream_health(client, workspace_id):
    stream = await _add_stream(client, workspace_id)
    resp = await client.get(f"/api/command-center/streams/{stream['id']}/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "online"


@pytest.mark.anyio
async def test_remove_stream(client, workspace_id):
    stream = await _add_stream(client, workspace_id)

    resp = await client.delete(
        f"/api/command-center/streams/{stream['id']}?workspace_id={workspace_id}"
    )
    assert resp.status_code == 204

    listing = await client.get(
        f"/api/command-center/streams?workspace_id={workspace_id}"
    )
    assert listing.json() == []


@pytest.mark.anyio
async def test_remove_unknown_stream_404s(client, workspace_id):
    resp = await client.delete(
        f"/api/command-center/streams/{uuid.uuid4()}?workspace_id={workspace_id}"
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_streams_status_counts(client, workspace_id):
    """The agent panels' /api/streams/status reports active and total."""
    await _add_stream(client, workspace_id, "a")
    await _add_stream(client, workspace_id, "b")

    resp = await client.get(f"/api/streams/status?workspace_id={workspace_id}")
    assert resp.json() == {"active": 2, "total": 2}


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_layout_round_trip(client, workspace_id):
    """PUT /layout is what the console sends; GET must read it back."""
    assert (
        await client.get(f"/api/command-center/layout?workspace_id={workspace_id}")
    ).json()["layout"] == "2x2"

    put = await client.put(
        f"/api/command-center/layout?workspace_id={workspace_id}",
        json={"layout": "3x3"},
    )
    assert put.status_code == 200
    assert put.json() == {"layout": "3x3"}

    assert (
        await client.get(f"/api/command-center/layout?workspace_id={workspace_id}")
    ).json()["layout"] == "3x3"


@pytest.mark.anyio
async def test_layout_rejects_unknown_preset(client, workspace_id):
    resp = await client.put(
        f"/api/command-center/layout?workspace_id={workspace_id}",
        json={"layout": "9x9"},
    )
    assert resp.status_code in (422, 500)


# ---------------------------------------------------------------------------
# Shifts
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_create_and_end_shift(client, workspace_id):
    """The console sends only a zone; the shift resolves to the workspace owner."""
    created = await client.post(
        f"/api/command-center/shifts?workspace_id={workspace_id}",
        json={"zone": "zone-A"},
    )
    assert created.status_code == 201, created.text
    shift = created.json()
    assert shift["zone"] == "zone-A"
    assert shift["started_at"]
    assert shift["ended_at"] is None
    assert shift["operator_id"]

    ended = await client.put(
        f"/api/command-center/shifts/{shift['id']}/end",
        json={"handoff_notes": "Watch zone B"},
    )
    assert ended.status_code == 200
    assert ended.json()["ended_at"] is not None
    assert ended.json()["handoff_notes"] == "Watch zone B"


@pytest.mark.anyio
async def test_list_shifts(client, workspace_id):
    await client.post(
        f"/api/command-center/shifts?workspace_id={workspace_id}",
        json={"zone": "zone-A"},
    )

    resp = await client.get(f"/api/command-center/shifts?workspace_id={workspace_id}")
    assert resp.status_code == 200
    assert [s["zone"] for s in resp.json()] == ["zone-A"]


@pytest.mark.anyio
async def test_end_unknown_shift_404s(client):
    resp = await client.put(
        f"/api/command-center/shifts/{uuid.uuid4()}/end", json={}
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_shift_without_operator_or_owner_is_rejected(client, cc_env):
    """A workspace with no owner cannot silently invent an operator."""
    factory, _ = cc_env
    ownerless = uuid.uuid4()
    async with factory() as session:
        session.add(
            Workspace(
                id=ownerless, name="ownerless", slug=f"own-{uuid.uuid4().hex[:8]}"
            )
        )
        await session.commit()

    resp = await client.post(
        f"/api/command-center/shifts?workspace_id={ownerless}", json={"zone": "z"}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_incident_queue_shape(client, workspace_id, cc_env):
    factory, _ = cc_env
    await _seed_incident(factory, workspace_id)

    resp = await client.get(
        f"/api/command-center/incidents?workspace_id={workspace_id}"
    )
    assert resp.status_code == 200
    incidents = resp.json()

    assert len(incidents) == 1
    incident = incidents[0]
    assert incident["title"] == "Perimeter breach"
    assert incident["severity"] == "critical"
    assert incident["status"] == "active"
    assert incident["created_at"]


@pytest.mark.anyio
async def test_assign_escalate_resolve(client, workspace_id, cc_env):
    """Each queue action moves the incident's stored status."""
    factory, _ = cc_env
    incident_id = await _seed_incident(factory, workspace_id)

    assigned = await client.post(
        f"/api/command-center/incidents/{incident_id}/assign"
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "assigned"
    assert assigned.json()["assigned_to"]

    escalated = await client.post(
        f"/api/command-center/incidents/{incident_id}/escalate"
    )
    assert escalated.json()["status"] == "escalated"

    resolved = await client.post(
        f"/api/command-center/incidents/{incident_id}/resolve"
    )
    assert resolved.json()["status"] == "resolved"

    # Resolved incidents drop out of the active queue.
    queue = await client.get(
        f"/api/command-center/incidents?workspace_id={workspace_id}"
    )
    assert queue.json() == []


@pytest.mark.anyio
async def test_unknown_incident_404s(client):
    resp = await client.post(
        f"/api/command-center/incidents/{uuid.uuid4()}/resolve"
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Overview, KPIs, timeline
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_overview_reflects_real_state(client, workspace_id, cc_env):
    """Overview counts streams, incidents and operators actually in the tables."""
    factory, _ = cc_env
    await _add_stream(client, workspace_id)
    await _seed_incident(factory, workspace_id)
    await client.post(
        f"/api/command-center/shifts?workspace_id={workspace_id}",
        json={"zone": "zone-A"},
    )

    resp = await client.get(f"/api/command-center/overview?workspace_id={workspace_id}")
    assert resp.status_code == 200
    overview = resp.json()

    assert overview["active_streams"] == 1
    assert overview["open_incidents"] == 1
    assert overview["active_operators"] == 1
    assert overview["current_layout"] == "2x2"
    assert overview["system_status"] in {"green", "yellow", "red"}


@pytest.mark.anyio
async def test_kpis_shape(client, workspace_id):
    """KPI keys match the console's KPIs interface."""
    resp = await client.get(f"/api/command-center/kpis?workspace_id={workspace_id}")
    assert resp.status_code == 200

    assert set(resp.json()) == {
        "avg_response_time_seconds",
        "response_time_trend",
        "resolution_rate_pct",
        "resolution_rate_trend",
        "false_alarm_rate_pct",
        "false_alarm_trend",
        "incidents_today",
        "incidents_today_trend",
    }


@pytest.mark.anyio
async def test_timeline_reports_incidents(client, workspace_id, cc_env):
    factory, _ = cc_env
    await _seed_incident(factory, workspace_id, "Camera tampering")

    resp = await client.get(f"/api/command-center/timeline?workspace_id={workspace_id}")
    assert resp.status_code == 200
    entries = resp.json()

    assert entries
    assert any("Camera tampering" in e["description"] for e in entries)
    for entry in entries:
        assert entry["type"] in {"alert", "incident", "stream", "operator", "system"}
        assert entry["timestamp"]


# ---------------------------------------------------------------------------
# Durability
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_command_center_state_survives_a_restart(client, workspace_id, cc_env):
    """Streams, layout, shifts and incidents all come back after a restart.

    State is written through the app, then read through a brand-new engine —
    a fresh pool and identity map, so nothing survives in process memory.
    """
    factory, _ = cc_env

    stream = await _add_stream(client, workspace_id, "durable-cam")
    await client.put(
        f"/api/command-center/layout?workspace_id={workspace_id}",
        json={"layout": "4x4"},
    )
    await client.post(
        f"/api/command-center/shifts?workspace_id={workspace_id}",
        json={"zone": "durable-zone"},
    )
    incident_id = await _seed_incident(factory, workspace_id, "Durable incident")

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)

    async def _override_get_db():
        async with restarted() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as fresh:
            streams = await fresh.get(
                f"/api/command-center/streams?workspace_id={workspace_id}"
            )
            assert [s["id"] for s in streams.json()] == [stream["id"]]
            assert streams.json()[0]["name"] == "durable-cam"

            layout = await fresh.get(
                f"/api/command-center/layout?workspace_id={workspace_id}"
            )
            assert layout.json()["layout"] == "4x4"

            shifts = await fresh.get(
                f"/api/command-center/shifts?workspace_id={workspace_id}"
            )
            assert [s["zone"] for s in shifts.json()] == ["durable-zone"]

            incidents = await fresh.get(
                f"/api/command-center/incidents?workspace_id={workspace_id}"
            )
            assert [i["id"] for i in incidents.json()] == [incident_id]
    finally:
        app.dependency_overrides.pop(get_db, None)
        await restarted_engine.dispose()
