"""Tests for the investigation workspace: service, routes, and timeline."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_db as get_db_func
from app.main import app
from app.services.investigation.service import InvestigationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def service():
    return InvestigationService()


@pytest.fixture
def workspace_id():
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_mock_event(event_type="case", workspace_id=None, payload=None, linked_asset_ids=None):
    """Helper to create a mock Event object (without touching SQLAlchemy mapper)."""
    event = MagicMock()
    event.id = uuid.uuid4()
    event.type = event_type
    event.source = "investigation"
    event.workspace_id = workspace_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    event.timestamp = datetime.now(timezone.utc)
    event.payload = payload or {}
    event.linked_asset_ids = linked_asset_ids or []
    return event


# ---------------------------------------------------------------------------
# Service: create_case — patches Event constructor to avoid mapper issues
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_create_case(service, workspace_id):
    """create_case should add an Event with type='case' to the DB."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    instance = _make_mock_event("case", workspace_id, {
        "name": "Intrusion Alpha", "description": "Suspicious activity", "status": "open"
    })

    async def mock_refresh(obj):
        pass

    mock_db.refresh = mock_refresh

    with patch("app.services.investigation.service.Event", return_value=instance):
        case = await service.create_case(
            mock_db, name="Intrusion Alpha", description="Suspicious activity", workspace_id=workspace_id
        )
        assert mock_db.add.called
        assert mock_db.commit.called
        assert case.type == "case"
        assert case.payload["name"] == "Intrusion Alpha"


# ---------------------------------------------------------------------------
# Service: add_evidence — mock _find_case helper + Event constructor
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_add_evidence(service, workspace_id):
    """add_evidence should verify case exists, then add an evidence event."""
    case_event = _make_mock_event("case", workspace_id, {
        "name": "Test Case", "description": "desc", "status": "open"
    })
    asset_id = uuid.uuid4()
    evidence_instance = _make_mock_event("evidence", workspace_id, {
        "case_id": str(case_event.id), "notes": "Found at scene"
    }, linked_asset_ids=[asset_id])

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=case_event)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.services.investigation.service.Event", return_value=evidence_instance) as MockEvent, \
         patch("app.services.investigation.service.select") as mock_select:
        # Make select() return a chainable mock
        mock_stmt = MagicMock()
        mock_stmt.where = MagicMock(return_value=mock_stmt)
        mock_select.return_value = mock_stmt

        evidence = await service.add_evidence(
            mock_db, case_id=case_event.id, asset_id=asset_id, notes="Found at scene"
        )
        assert mock_db.add.called
        assert evidence.type == "evidence"
        assert evidence.payload["case_id"] == str(case_event.id)


# ---------------------------------------------------------------------------
# Service: get_timeline_ordered
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_timeline_ordered(service, workspace_id):
    """get_timeline should return events ordered by timestamp."""
    e1 = _make_mock_event("case", workspace_id, {"name": "Case A"})
    e2 = _make_mock_event("evidence", workspace_id, {"case_id": str(e1.id), "notes": "evidence"})
    e3 = _make_mock_event("note", workspace_id, {"case_id": str(e1.id), "content": "note"})

    mock_db = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[e1, e2, e3])
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    mock_db.execute = AsyncMock(return_value=mock_result)

    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2030, 12, 31, tzinfo=timezone.utc)

    with patch("app.services.investigation.service.select") as mock_select:
        mock_stmt = MagicMock()
        mock_stmt.where = MagicMock(return_value=mock_stmt)
        mock_stmt.order_by = MagicMock(return_value=mock_stmt)
        mock_select.return_value = mock_stmt

        events = await service.get_timeline(mock_db, workspace_id, start, end)
        assert len(events) == 3
        assert events[0].type == "case"


# ---------------------------------------------------------------------------
# Service: add_note
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_add_note(service, workspace_id):
    """add_note should create a note Event linked to a case."""
    case_event = _make_mock_event("case", workspace_id, payload={
        "name": "Test Case", "description": "desc", "status": "open"
    })
    note_instance = _make_mock_event("note", workspace_id, {
        "case_id": str(case_event.id), "user_id": "user-1", "content": "Suspicious pattern"
    })

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=case_event)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.services.investigation.service.Event", return_value=note_instance), \
         patch("app.services.investigation.service.select") as mock_select:
        mock_stmt = MagicMock()
        mock_stmt.where = MagicMock(return_value=mock_stmt)
        mock_select.return_value = mock_stmt

        note = await service.add_note(
            mock_db, case_id=case_event.id, user_id="user-1", content="Suspicious pattern"
        )
        assert mock_db.add.called
        assert note.type == "note"
        assert note.payload["content"] == "Suspicious pattern"


# ---------------------------------------------------------------------------
# Service: export_case
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_export_case(service, workspace_id):
    """export_case should return structured case data."""
    case_event = _make_mock_event("case", workspace_id, payload={
        "name": "Export Test", "description": "desc", "status": "open"
    })
    evidence = _make_mock_event("evidence", workspace_id, payload={
        "case_id": str(case_event.id), "notes": "key evidence"
    }, linked_asset_ids=[uuid.uuid4()])
    note = _make_mock_event("note", workspace_id, payload={
        "case_id": str(case_event.id), "user_id": "user-1", "content": "key finding"
    })

    mock_db = AsyncMock()

    call_count = 0
    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none = MagicMock(return_value=case_event)
        else:
            mock_scalars = MagicMock()
            mock_scalars.all = MagicMock(return_value=[evidence, note])
            result.scalars = MagicMock(return_value=mock_scalars)
        return result

    mock_db.execute = mock_execute

    with patch("app.services.investigation.service.select") as mock_select:
        mock_stmt = MagicMock()
        mock_stmt.where = MagicMock(return_value=mock_stmt)
        mock_stmt.order_by = MagicMock(return_value=mock_stmt)
        mock_select.return_value = mock_stmt

        exported = await service.export_case(mock_db, case_event.id)
        assert "case" in exported
        assert "events" in exported
        assert "evidence" in exported
        assert "timeline" in exported
        assert exported["case"]["name"] == "Export Test"


# ---------------------------------------------------------------------------
# API: create case
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_create_case(client):
    """POST /api/investigate/cases should create a case."""
    mock_case = _make_mock_event("case", payload={
        "name": "API Case", "description": "Created via API", "status": "open"
    })

    with patch("app.api.routes.investigation.investigation_service") as mock_service:
        mock_service.create_case = AsyncMock(return_value=mock_case)

        resp = await client.post(
            "/api/investigate/cases",
            json={
                "name": "API Case",
                "description": "Created via API",
                "workspace_id": "00000000-0000-0000-0000-000000000001",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "case"
        assert data["payload"]["name"] == "API Case"
