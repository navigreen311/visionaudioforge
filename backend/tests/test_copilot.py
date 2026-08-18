"""Tests for the agentic media copilot: service, memory, tools, and API."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_db as get_db_func
from app.main import app
from app.services.agents.copilot import CopilotService
from app.services.agents.memory import AgentMemoryService
from app.services.agents.skill_packs import SKILL_PACKS
from app.services.agents.tools import COPILOT_TOOLS, execute_tool


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
def copilot():
    return CopilotService()


@pytest.fixture
def memory_service():
    return AgentMemoryService()


# ---------------------------------------------------------------------------
# CopilotService tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_build_system_prompt_includes_tools(copilot):
    """System prompt should list available tool names."""
    # _build_system_prompt is a coroutine; without the await this asserted
    # "name in <coroutine>", which raises TypeError rather than checking
    # anything about the prompt.
    prompt = await copilot._build_system_prompt(
        workspace_id="ws-1",
        agent_id="agent-1",
        skill_pack="general",
    )
    for tool in COPILOT_TOOLS:
        assert tool["name"] in prompt, f"Tool {tool['name']} not in system prompt"


# ---------------------------------------------------------------------------
# Skill packs tests
# ---------------------------------------------------------------------------

def test_skill_packs_all_defined():
    """All 7 expected skill packs should exist."""
    expected = [
        "general",
        "investigator",
        "qa_analyst",
        "compliance",
        "media_editor",
        "operations",
        "executive",
    ]
    for pack in expected:
        assert pack in SKILL_PACKS, f"Skill pack '{pack}' missing"
    assert len(SKILL_PACKS) == 7


# ---------------------------------------------------------------------------
# Memory service tests (using mock DB)
# ---------------------------------------------------------------------------

def _make_mock_memory(content="test", importance=0.5, freshness=1.0):
    mem = MagicMock()
    mem.id = uuid.uuid4()
    mem.content = content
    mem.importance_score = importance
    mem.freshness_score = freshness
    mem.created_at = None
    return mem


@pytest.mark.anyio
async def test_memory_store_and_recall(memory_service):
    """store_memory should add a record via the DB session."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    await memory_service.store_memory(
        mock_db, agent_id="a1", content="important finding", importance_score=0.7
    )
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.anyio
async def test_memory_decay_reduces_freshness(memory_service):
    """decay_memories should execute update and commit."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    await memory_service.decay_memories(mock_db, agent_id="a1", decay_factor=0.9)
    assert mock_db.execute.called
    assert mock_db.commit.called


@pytest.mark.anyio
async def test_memory_promote_increases_importance(memory_service):
    """promote_memory should update importance score."""
    mock_db = AsyncMock()
    mock_mem = _make_mock_memory("old finding", 0.3, 0.8)

    mock_result = MagicMock()
    mock_result.scalar_one = MagicMock(return_value=mock_mem)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    updated = await memory_service.promote_memory(mock_db, str(mock_mem.id), 0.95)
    assert updated.importance_score == 0.95


# ---------------------------------------------------------------------------
# Tool definition tests
# ---------------------------------------------------------------------------

def test_tool_definitions_valid_schema():
    """Each tool should have name, description, and valid input_schema."""
    for tool in COPILOT_TOOLS:
        assert "name" in tool, "Tool missing 'name'"
        assert "description" in tool, f"Tool {tool['name']} missing 'description'"
        assert "input_schema" in tool, f"Tool {tool['name']} missing 'input_schema'"

        schema = tool["input_schema"]
        assert schema["type"] == "object", f"Tool {tool['name']} schema type must be 'object'"
        assert "properties" in schema, f"Tool {tool['name']} missing properties"


@pytest.mark.anyio
async def test_tool_execute_search_media():
    """execute_tool for search_media should return JSON with results."""
    import json

    result = await execute_tool("search_media", {"query": "sunset", "modality": "image"})
    data = json.loads(result)
    assert "results" in data
    assert data["query"] == "sunset"
    assert data["modality"] == "image"


@pytest.mark.anyio
async def test_tool_execute_system_status():
    """execute_tool for get_system_status should return health info."""
    import json

    result = await execute_tool("get_system_status", {})
    data = json.loads(result)
    assert data["status"] == "healthy"
    assert "services" in data


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_chat_returns_response(client):
    """POST /api/agents/chat should return a response with mock copilot."""
    with patch("app.api.routes.agents.memory_service") as mock_mem:
        mock_mem.recall = AsyncMock(return_value=[])
        mock_mem.store_memory = AsyncMock()

        resp = await client.post(
            "/api/agents/chat",
            json={"message": "Hello copilot", "skill_pack": "general"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "agent_id" in data
    assert "memories_used" in data


@pytest.mark.anyio
async def test_api_list_agents(client):
    """GET /api/agents should return a list."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db_func] = _get_db
    try:
        resp = await client.get("/api/agents")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_create_agent(client):
    """POST /api/agents should create a new agent."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    agent_mock = MagicMock()
    agent_mock.id = uuid.uuid4()
    agent_mock.name = "Test Agent"
    agent_mock.agent_type = "copilot"
    agent_mock.status = "idle"
    agent_mock.created_at = MagicMock(
        isoformat=MagicMock(return_value="2026-03-20T00:00:00")
    )

    async def mock_refresh(obj):
        obj.id = agent_mock.id
        obj.name = agent_mock.name
        obj.agent_type = agent_mock.agent_type
        obj.status = agent_mock.status
        obj.created_at = agent_mock.created_at

    mock_db.refresh = mock_refresh

    async def _get_db():
        yield mock_db

    app.dependency_overrides[get_db_func] = _get_db
    try:
        resp = await client.post(
            "/api/agents",
            json={"name": "Test Agent", "agent_type": "copilot"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Agent"
    finally:
        app.dependency_overrides.clear()
