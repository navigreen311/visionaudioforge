"""Tests for the Command Center — streams, shifts, incident queue, and dashboard."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.command_center.stream_manager import StreamManager
from app.services.command_center.operator import OperatorService
from app.services.command_center.incident_queue import IncidentQueueService
from app.services.command_center.dashboard import CockpitDashboard

WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
OPERATOR_ID = "00000000-0000-0000-0000-000000000010"
OPERATOR_ID_2 = "00000000-0000-0000-0000-000000000020"


# ── Helpers ───────────────────────────────────────────────────────────


def _make_stream_row(sid=None, name="cam-1", position=0, status_val="connected", fps=30.0, latency=12.5):
    """Create a mock stream row."""
    row = MagicMock()
    row.id = sid or uuid.uuid4()
    row.name = name
    row.source_type = MagicMock(value="rtsp")
    row.position = position
    row.status = MagicMock(value=status_val)
    row.fps = fps
    row.latency_ms = latency
    row.last_frame_at = datetime.now(timezone.utc)
    row.workspace_id = uuid.UUID(WORKSPACE_ID)
    return row


def _make_shift_row(shift_id=None, operator_id=OPERATOR_ID, active=1, events=5):
    row = MagicMock()
    row.id = shift_id or uuid.uuid4()
    row.operator_id = uuid.UUID(operator_id)
    row.workspace_id = uuid.UUID(WORKSPACE_ID)
    row.start_time = datetime.now(timezone.utc) - timedelta(hours=4)
    row.end_time = datetime.now(timezone.utc)
    row.zone_assignment = "zone-A"
    row.is_active = active
    row.handoff_notes = None
    row.events_handled = events
    return row


def _make_incident_row(iid=None, severity="high", status="active", assigned=None, created_ago_s=300):
    from app.models.command_center import IncidentSeverity, IncidentStatus
    row = MagicMock()
    row.id = iid or uuid.uuid4()
    row.title = f"Test incident {severity}"
    row.severity = IncidentSeverity(severity)
    row.status = IncidentStatus(status)
    row.assigned_to = uuid.UUID(assigned) if assigned else None
    row.escalation_level = 0
    row.created_at = datetime.now(timezone.utc) - timedelta(seconds=created_ago_s)
    row.workspace_id = uuid.UUID(WORKSPACE_ID)
    row.response_time_s = None
    row.payload = {}
    row.resolved_at = None
    return row


# ── Stream Manager Tests ─────────────────────────────────────────────


@pytest.mark.anyio
async def test_add_remove_stream():
    """StreamManager.add_stream creates a stream; remove_stream deletes it."""
    db = AsyncMock()
    stream_mock = _make_stream_row(name="entrance-cam")

    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    # Mock the position query
    pos_result = MagicMock()
    pos_result.scalar.return_value = -1

    # Mock the select for remove
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = stream_mock

    db.execute = AsyncMock(side_effect=[pos_result, select_result])
    db.delete = AsyncMock()

    # Patch the refresh to set attributes on the added object
    async def _refresh(obj):
        obj.id = stream_mock.id
        obj.name = "entrance-cam"
        obj.source_type = stream_mock.source_type
        obj.position = 0
        obj.status = stream_mock.status

    db.refresh = AsyncMock(side_effect=_refresh)

    result = await StreamManager.add_stream(
        db, WORKSPACE_ID, "entrance-cam", "rtsp", {"url": "rtsp://host/1"}
    )
    assert result["name"] == "entrance-cam"
    assert result["status"] == "connected"
    assert result["position"] == 0

    # Remove
    db.execute = AsyncMock(return_value=select_result)
    removed = await StreamManager.remove_stream(db, WORKSPACE_ID, str(stream_mock.id))
    assert removed is True


@pytest.mark.anyio
async def test_layout_management():
    """StreamManager can get and set layout presets."""
    db = AsyncMock()

    # get_layout — no existing row
    layout_result = MagicMock()
    layout_result.scalar_one_or_none.return_value = None
    streams_result = MagicMock()
    streams_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[layout_result, streams_result])

    layout = await StreamManager.get_layout(db, WORKSPACE_ID)
    assert layout["layout"] == "2x2"
    assert layout["streams"] == []

    # set_layout
    db.add = MagicMock()
    db.commit = AsyncMock()
    set_layout_result = MagicMock()
    set_layout_result.scalar_one_or_none.return_value = None
    get_layout_result = MagicMock()
    get_layout_result.scalar_one_or_none.return_value = MagicMock(layout="3x3")
    streams_result2 = MagicMock()
    streams_result2.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[set_layout_result, get_layout_result, streams_result2])

    result = await StreamManager.set_layout(db, WORKSPACE_ID, "3x3")
    assert result["layout"] == "3x3"


@pytest.mark.anyio
async def test_stream_health():
    """StreamManager.get_stream_health returns per-stream metrics."""
    db = AsyncMock()
    s1 = _make_stream_row(name="cam-1", fps=30.0, latency=15.0)
    s2 = _make_stream_row(name="cam-2", fps=25.0, latency=20.0, status_val="buffering")

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [s1, s2]
    db.execute = AsyncMock(return_value=result_mock)

    health = await StreamManager.get_stream_health(db, WORKSPACE_ID)
    assert len(health) == 2
    assert health[0]["fps"] == 30.0
    assert health[1]["status"] == "buffering"
    assert health[1]["latency_ms"] == 20.0


# ── Operator / Shift Tests ───────────────────────────────────────────


@pytest.mark.anyio
async def test_create_end_shift():
    """OperatorService can create and end a shift."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    shift_id = uuid.uuid4()

    async def _refresh(obj):
        obj.id = shift_id

    db.refresh = AsyncMock(side_effect=_refresh)

    now = datetime.now(timezone.utc)
    result = await OperatorService.create_shift(
        db, WORKSPACE_ID, OPERATOR_ID, now, now + timedelta(hours=8), zone_assignment="zone-A"
    )
    assert result["shift_id"] == str(shift_id)

    # End shift
    shift_row = _make_shift_row(shift_id=shift_id)
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = shift_row
    db.execute = AsyncMock(return_value=select_result)

    end_result = await OperatorService.end_shift(db, str(shift_id), handoff_notes="All clear")
    assert end_result["shift_id"] == str(shift_id)
    assert end_result["duration_h"] > 0
    assert end_result["events_handled"] == 5


@pytest.mark.anyio
async def test_shift_handoff():
    """Ending a shift with handoff notes records them properly."""
    db = AsyncMock()
    db.commit = AsyncMock()

    shift_row = _make_shift_row()
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = shift_row
    db.execute = AsyncMock(return_value=select_result)

    result = await OperatorService.end_shift(db, str(shift_row.id), handoff_notes="Watch zone B closely")
    assert result["shift_id"] == str(shift_row.id)
    assert shift_row.handoff_notes == "Watch zone B closely"


# ── Incident Queue Tests ─────────────────────────────────────────────


@pytest.mark.anyio
async def test_incident_queue_sorted():
    """Incidents are returned sorted by severity (critical first) then time."""
    db = AsyncMock()

    # Create incidents with different severities
    i_low = _make_incident_row(severity="low", created_ago_s=100)
    i_crit = _make_incident_row(severity="critical", created_ago_s=200)
    i_high = _make_incident_row(severity="high", created_ago_s=150)

    # Simulate DB returning them already sorted (as the query would)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [i_crit, i_high, i_low]
    db.execute = AsyncMock(return_value=result_mock)

    queue = await IncidentQueueService.get_queue(db, WORKSPACE_ID)
    assert len(queue) == 3
    assert queue[0]["severity"] == "critical"
    assert queue[1]["severity"] == "high"
    assert queue[2]["severity"] == "low"


@pytest.mark.anyio
async def test_assign_incident():
    """Assigning an incident sets the operator and status."""
    db = AsyncMock()
    db.commit = AsyncMock()

    incident = _make_incident_row(severity="high")
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = incident
    db.execute = AsyncMock(return_value=select_result)

    result = await IncidentQueueService.assign_incident(db, str(incident.id), OPERATOR_ID)
    assert result["assigned_to"] == OPERATOR_ID
    assert result["status"] == "assigned"


@pytest.mark.anyio
async def test_auto_assign_roundrobin():
    """auto_assign distributes incidents round-robin across active operators."""
    db = AsyncMock()
    db.commit = AsyncMock()

    # Two active operators
    ops_result = MagicMock()
    ops_result.all.return_value = [
        (uuid.UUID(OPERATOR_ID),),
        (uuid.UUID(OPERATOR_ID_2),),
    ]

    # Three unassigned incidents
    i1 = _make_incident_row(severity="critical")
    i2 = _make_incident_row(severity="high")
    i3 = _make_incident_row(severity="medium")
    inc_result = MagicMock()
    inc_result.scalars.return_value.all.return_value = [i1, i2, i3]

    db.execute = AsyncMock(side_effect=[ops_result, inc_result])

    result = await IncidentQueueService.auto_assign(db, WORKSPACE_ID)
    assert result["assigned"] == 3

    # Round-robin: op1, op2, op1
    assert i1.assigned_to == uuid.UUID(OPERATOR_ID)
    assert i2.assigned_to == uuid.UUID(OPERATOR_ID_2)
    assert i3.assigned_to == uuid.UUID(OPERATOR_ID)


@pytest.mark.anyio
async def test_queue_stats():
    """get_queue_stats returns correct aggregate metrics."""
    db = AsyncMock()

    # total_active
    total_result = MagicMock()
    total_result.scalar.return_value = 5

    # by_severity
    from app.models.command_center import IncidentSeverity
    sev_result = MagicMock()
    sev_result.all.return_value = [
        (IncidentSeverity.critical, 2),
        (IncidentSeverity.high, 3),
    ]

    # avg response
    avg_result = MagicMock()
    avg_result.scalar.return_value = 45.5

    # unassigned
    unassigned_result = MagicMock()
    unassigned_result.scalar.return_value = 2

    # oldest
    oldest_result = MagicMock()
    oldest_result.scalar.return_value = datetime.now(timezone.utc) - timedelta(minutes=30)

    db.execute = AsyncMock(side_effect=[
        total_result, sev_result, avg_result, unassigned_result, oldest_result,
    ])

    stats = await IncidentQueueService.get_queue_stats(db, WORKSPACE_ID)
    assert stats["total_active"] == 5
    assert stats["by_severity"]["critical"] == 2
    assert stats["by_severity"]["high"] == 3
    assert stats["avg_response_time_s"] == 45.5
    assert stats["unassigned"] == 2
    assert stats["oldest_unresolved_age_s"] > 0


# ── Dashboard Tests ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_cockpit_overview():
    """CockpitDashboard.get_overview returns aggregated metrics."""
    db = AsyncMock()

    # active_streams=3, active_operators=2, open_incidents=1, alerts_24h=5
    streams_result = MagicMock(); streams_result.scalar.return_value = 3
    ops_result = MagicMock(); ops_result.scalar.return_value = 2
    inc_result = MagicMock(); inc_result.scalar.return_value = 1
    alerts_result = MagicMock(); alerts_result.scalar.return_value = 5

    from app.models.command_center import StreamStatus
    health_result = MagicMock()
    health_result.all.return_value = [(StreamStatus.connected, 3)]

    db.execute = AsyncMock(side_effect=[
        streams_result, ops_result, inc_result, alerts_result, health_result,
    ])

    overview = await CockpitDashboard.get_overview(db, WORKSPACE_ID)
    assert overview["active_streams"] == 3
    assert overview["active_operators"] == 2
    assert overview["open_incidents"] == 1
    assert overview["alerts_24h"] == 5
    assert overview["system_status"] == "warning"


@pytest.mark.anyio
async def test_kpis():
    """CockpitDashboard.get_kpis returns performance metrics."""
    db = AsyncMock()

    avg_result = MagicMock(); avg_result.scalar.return_value = 30.0
    total_result = MagicMock(); total_result.scalar.return_value = 10
    resolved_result = MagicMock(); resolved_result.scalar.return_value = 8
    dismissed_result = MagicMock(); dismissed_result.scalar.return_value = 1
    total_streams_result = MagicMock(); total_streams_result.scalar.return_value = 4
    connected_result = MagicMock(); connected_result.scalar.return_value = 4

    db.execute = AsyncMock(side_effect=[
        avg_result, total_result, resolved_result, dismissed_result,
        total_streams_result, connected_result,
    ])

    kpis = await CockpitDashboard.get_kpis(db, WORKSPACE_ID, period="daily")
    assert kpis["avg_response_time_s"] == 30.0
    assert kpis["incident_resolution_rate"] == 0.8
    assert kpis["false_alarm_rate"] == 0.1
    assert kpis["uptime_pct"] == 100.0


@pytest.mark.anyio
async def test_timeline_feed():
    """CockpitDashboard.get_timeline_feed returns merged events and incidents."""
    db = AsyncMock()

    # Mock events
    event = MagicMock()
    event.id = uuid.uuid4()
    event.type = "alert_triggered"
    event.payload = {"note": "Motion detected"}
    event.timestamp = datetime.now(timezone.utc)

    events_result = MagicMock()
    events_result.scalars.return_value.all.return_value = [event]

    # Mock incidents
    inc = _make_incident_row(severity="critical")

    inc_result = MagicMock()
    inc_result.scalars.return_value.all.return_value = [inc]

    db.execute = AsyncMock(side_effect=[events_result, inc_result])

    timeline = await CockpitDashboard.get_timeline_feed(db, WORKSPACE_ID, limit=50)
    assert len(timeline) == 2
    types = {t["type"] for t in timeline}
    assert "alert_triggered" in types
    assert "incident" in types


# ── API Route Tests ──────────────────────────────────────────────────


# The route-level tests that used to live here drove the endpoints against the
# app's configured database and accepted 200-or-500, which passed whether or
# not anything worked. Now that these routes read and write real tables, they
# are covered properly in tests/test_command_center_api.py, which runs them
# against a live database and asserts the response bodies the console reads.
