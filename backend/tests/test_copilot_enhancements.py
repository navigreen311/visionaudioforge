"""Tests for copilot enhancements: real tool execution, conversation, patrol, and context enrichment."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_db as get_db_func
from app.main import app
from app.services.agents.conversation import ConversationManager
from app.services.agents.copilot import CopilotService
from app.services.agents.patrol import PatrolAgent
from app.services.agents.tools import execute_tool


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
def conversation_manager():
    return ConversationManager()


# ---------------------------------------------------------------------------
# 1. Tool execution handles missing services gracefully
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_tool_execution_handles_missing_service():
    """Tools should return error info instead of crashing when services are unavailable."""
    # search_media — will fail because EmbeddingService/FAISS won't have real models
    result = await execute_tool("search_media", {"query": "test", "modality": "text"})
    data = json.loads(result)
    # Should have results (empty) or a note about unavailability — not raise
    assert "query" in data
    assert "results" in data or "note" in data

    # analyze_image — non-existent path
    result = await execute_tool("analyze_image", {"image_path": "/nonexistent/image.jpg"})
    data = json.loads(result)
    assert "image_path" in data
    # Should get an error message, not a crash
    assert "error" in data or "objects_detected" in data

    # analyze_audio — non-existent path
    result = await execute_tool("analyze_audio", {"audio_path": "/nonexistent/audio.wav"})
    data = json.loads(result)
    assert "audio_path" in data
    assert "error" in data or "duration_seconds" in data

    # get_system_status — should work even without real services
    result = await execute_tool("get_system_status", {})
    data = json.loads(result)
    assert "status" in data
    assert "services" in data

    # Unknown tool
    result = await execute_tool("nonexistent_tool", {})
    data = json.loads(result)
    assert "error" in data


# ---------------------------------------------------------------------------
# 2. Conversation store and retrieve
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_conversation_store_retrieve(conversation_manager):
    """ConversationManager should store and retrieve messages via DB."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Store a message
    await conversation_manager.store_message(
        mock_db, agent_id="agent-test", role="user", content="Hello there"
    )
    assert mock_db.add.called
    assert mock_db.commit.called

    # Verify the Event was constructed correctly
    added_obj = mock_db.add.call_args[0][0]
    assert added_obj.type == "chat_message"
    assert added_obj.payload["role"] == "user"
    assert added_obj.payload["content"] == "Hello there"
    assert added_obj.payload["agent_id"] == "agent-test"
    assert added_obj.source == "copilot"


@pytest.mark.anyio
async def test_conversation_context_window(conversation_manager):
    """get_context_window should respect token budget."""
    # Create mock messages
    mock_messages = [
        {"id": str(i), "role": "user" if i % 2 == 0 else "assistant",
         "content": "x" * 100, "timestamp": ""}
        for i in range(20)
    ]

    with patch.object(conversation_manager, "get_history", return_value=mock_messages):
        # With budget of 400 tokens (100 chars / 4 = 25 tokens per msg, so ~16 msgs)
        result = await conversation_manager.get_context_window(
            AsyncMock(), agent_id="test", max_tokens_approx=400
        )
        assert len(result) <= 16
        assert len(result) > 0


@pytest.mark.anyio
async def test_conversation_clear_history(conversation_manager):
    """clear_history should delete events and return count."""
    mock_db = AsyncMock()
    # Mock the select query to return some IDs
    mock_select_result = MagicMock()
    mock_select_result.all.return_value = [(uuid.uuid4(),), (uuid.uuid4(),)]
    # Mock the delete query
    mock_del_result = MagicMock()
    mock_del_result.rowcount = 2

    mock_db.execute = AsyncMock(side_effect=[mock_select_result, mock_del_result])
    mock_db.commit = AsyncMock()

    count = await conversation_manager.clear_history(mock_db, agent_id="agent-test")
    assert count == 2


# ---------------------------------------------------------------------------
# 3. Patrol cycle returns findings
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_patrol_cycle_returns_findings():
    """PatrolAgent.run_patrol_cycle should return a list of PatrolFinding dicts."""
    patrol = PatrolAgent(
        agent_id="patrol-test",
        workspace_id="00000000-0000-0000-0000-000000000000",
    )

    findings = await patrol.run_patrol_cycle()

    assert isinstance(findings, list)
    assert len(findings) > 0  # Should have at least system_health check

    for finding in findings:
        assert "check" in finding
        assert "status" in finding
        assert finding["status"] in ("ok", "warning", "critical")
        assert "message" in finding
        assert "timestamp" in finding


@pytest.mark.anyio
async def test_patrol_start_stop():
    """PatrolAgent start/stop lifecycle."""
    patrol = PatrolAgent(
        agent_id="lifecycle-test",
        workspace_id="00000000-0000-0000-0000-000000000000",
        check_interval_s=300,  # Long interval to avoid actual cycles during test
    )

    assert not patrol.is_running

    # Use a mock db_factory
    mock_factory = MagicMock()
    await patrol.start_patrol(db_factory=mock_factory)
    assert patrol.is_running

    await patrol.stop_patrol()
    assert not patrol.is_running


# ---------------------------------------------------------------------------
# 4. Context enrichment includes stats
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_context_enrichment_includes_stats():
    """System prompt should include workspace stats when DB is available."""
    copilot = CopilotService()

    mock_db = AsyncMock()

    # Mock DB queries for workspace stats
    mock_scalar_result = MagicMock()
    mock_scalar_result.scalar.return_value = 42
    mock_db.execute = AsyncMock(return_value=mock_scalar_result)

    prompt = await copilot._build_system_prompt(
        workspace_id="ws-test",
        agent_id="agent-test",
        skill_pack="general",
        memories=["test memory"],
        db=mock_db,
    )

    # Should contain basic sections
    assert "VisionAudioForge" in prompt
    assert "ws-test" in prompt
    assert "agent-test" in prompt
    assert "test memory" in prompt

    # Should contain tool names
    assert "search_media" in prompt
    assert "get_system_status" in prompt


@pytest.mark.anyio
async def test_context_enrichment_without_db():
    """System prompt should work fine without DB (no enrichment)."""
    copilot = CopilotService()
    prompt = await copilot._build_system_prompt(
        workspace_id="ws-1",
        agent_id="agent-1",
        skill_pack="operations",
        db=None,
    )
    assert "operations controller" in prompt.lower()
    assert "search_media" in prompt


# ---------------------------------------------------------------------------
# 5. API routes — patrol start
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_patrol_start(client):
    """POST /api/agents/{id}/patrol/start should return started status."""
    with patch("app.api.routes.agents.get_patrol_agent") as mock_get:
        mock_patrol = MagicMock()
        mock_patrol.is_running = False
        mock_patrol.start_patrol = AsyncMock()
        mock_get.return_value = mock_patrol

        resp = await client.post("/api/agents/test-agent/patrol/start")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
    assert data["agent_id"] == "test-agent"


@pytest.mark.anyio
async def test_api_patrol_stop(client):
    """POST /api/agents/{id}/patrol/stop should stop patrol."""
    with patch("app.api.routes.agents.get_patrol_agent") as mock_get:
        mock_patrol = MagicMock()
        mock_patrol.is_running = True
        mock_patrol.stop_patrol = AsyncMock()
        mock_get.return_value = mock_patrol

        resp = await client.post("/api/agents/test-agent/patrol/stop")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "stopped"


@pytest.mark.anyio
async def test_api_patrol_report(client):
    """GET /api/agents/{id}/patrol/report should return findings."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db_func] = _get_db

    with patch("app.api.routes.agents.get_patrol_agent") as mock_get:
        mock_patrol = MagicMock()
        mock_patrol.is_running = False
        mock_patrol.get_patrol_report = AsyncMock(return_value={
            "findings": [],
            "checks_run": 0,
            "warnings": 0,
            "critical": 0,
        })
        mock_get.return_value = mock_patrol

        try:
            resp = await client.get("/api/agents/test-agent/patrol/report")
            assert resp.status_code == 200
            data = resp.json()
            assert "findings" in data
            assert "checks_run" in data
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 6. API routes — history
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_history(client):
    """GET /api/agents/{id}/history should return conversation history."""
    mock_db = AsyncMock()

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db_func] = _get_db

    with patch("app.api.routes.agents.conversation_mgr") as mock_conv:
        mock_conv.get_history = AsyncMock(return_value=[
            {"id": "1", "role": "user", "content": "hello", "timestamp": "", "tool_use": None},
        ])

        try:
            resp = await client.get("/api/agents/test-agent/history")
            assert resp.status_code == 200
            data = resp.json()
            assert data["agent_id"] == "test-agent"
            assert len(data["messages"]) == 1
            assert data["count"] == 1
        finally:
            app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_clear_history(client):
    """DELETE /api/agents/{id}/history should clear conversation history."""
    mock_db = AsyncMock()

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db_func] = _get_db

    with patch("app.api.routes.agents.conversation_mgr") as mock_conv:
        mock_conv.clear_history = AsyncMock(return_value=5)

        try:
            resp = await client.delete("/api/agents/test-agent/history")
            assert resp.status_code == 200
            data = resp.json()
            assert data["deleted_count"] == 5
        finally:
            app.dependency_overrides.clear()
