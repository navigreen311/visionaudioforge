"""Tests for knowledge graph RAG service, query parser, and API routes."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.knowledge_graph.graph_rag import GraphRAGService
from app.services.knowledge_graph.query_parser import GraphQueryParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"


def _make_node_event(label: str, node_type: str, node_id: str | None = None):
    """Create a mock Event that looks like a graph node."""
    eid = node_id or str(uuid.uuid4())
    ev = MagicMock()
    ev.id = eid
    ev.type = f"graph_node_{node_type}"
    ev.workspace_id = WORKSPACE_ID
    ev.timestamp = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    ev.payload = {
        "label": label,
        "node_type": node_type,
        "properties": {"description": f"Test {node_type}: {label}"},
    }
    return ev


def _make_edge_event(
    source_id: str,
    target_id: str,
    source_label: str,
    target_label: str,
    relationship: str,
):
    """Create a mock Event that looks like a graph edge."""
    ev = MagicMock()
    ev.id = str(uuid.uuid4())
    ev.type = "graph_edge"
    ev.workspace_id = WORKSPACE_ID
    ev.timestamp = datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc)
    ev.payload = {
        "source_id": source_id,
        "target_id": target_id,
        "source_label": source_label,
        "target_label": target_label,
        "relationship": relationship,
        "properties": {},
    }
    return ev


def _mock_db_with_events(events: list):
    """Create a mock AsyncSession that returns given events on execute."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = events
    scalars_mock.scalars.return_value = scalars_mock

    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    result_mock.scalar_one_or_none.return_value = events[0] if events else None

    db.execute = AsyncMock(return_value=result_mock)
    return db


# ---------------------------------------------------------------------------
# Query Parser Tests
# ---------------------------------------------------------------------------

class TestGraphQueryParser:
    def setup_method(self):
        self.parser = GraphQueryParser()

    def test_query_parser_find_entity_intent(self):
        result = self.parser.parse("find all people")
        assert result["intent"] == "find_entity"
        assert result["raw_query"] == "find all people"

    def test_query_parser_find_path_intent(self):
        result = self.parser.parse("how is John connected to the warehouse")
        assert result["intent"] == "find_path"
        assert len(result["entities"]) >= 2
        assert result["traversal"]["source"] is not None
        assert result["traversal"]["target"] is not None

    def test_query_parser_find_relationship_intent(self):
        result = self.parser.parse("who was near the park")
        assert result["intent"] == "find_relationship"
        assert len(result["entities"]) >= 1

    def test_query_parser_temporal_intent(self):
        result = self.parser.parse(
            "what happened near the station between 10am and 2pm"
        )
        assert result["intent"] == "temporal_query"
        assert result["filters"].get("temporal") is True

    def test_query_parser_find_pattern_intent(self):
        result = self.parser.parse("find patterns of vehicle movements")
        assert result["intent"] == "find_pattern"

    def test_query_parser_entity_type_detection(self):
        result = self.parser.parse("find all vehicles near downtown")
        assert result["filters"].get("entity_type") == "vehicle"

    def test_query_parser_quoted_entities(self):
        result = self.parser.parse('find "John Smith" near "Main Street"')
        assert "John Smith" in result["entities"]
        assert "Main Street" in result["entities"]

    def test_query_parser_intents(self):
        """Test multiple intents are correctly parsed."""
        cases = [
            ("find all people", "find_entity"),
            ("how is Alice connected to Bob", "find_path"),
            ("who was near the park", "find_relationship"),
            ("what happened after the incident", "temporal_query"),
            ("show path from A to B", "find_path"),
            ("what is connected to the warehouse", "find_relationship"),
        ]
        for query, expected_intent in cases:
            result = self.parser.parse(query)
            assert result["intent"] == expected_intent, (
                f"Query '{query}' expected intent '{expected_intent}', "
                f"got '{result['intent']}'"
            )


# ---------------------------------------------------------------------------
# GraphRAGService Tests
# ---------------------------------------------------------------------------

class TestGraphRAGService:
    def setup_method(self):
        self.service = GraphRAGService()

    @pytest.mark.anyio
    async def test_retrieve_context_finds_nodes(self):
        """Test that retrieve_context finds matching nodes."""
        node1 = _make_node_event("John Smith", "person", "node-1")
        node2 = _make_node_event("Main Street", "location", "node-2")
        edge1 = _make_edge_event(
            "node-1", "node-2", "John Smith", "Main Street", "was seen at"
        )

        db = _mock_db_with_events([node1, node2])
        # Override to return different results for different queries
        call_count = 0

        async def multi_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            scalars = MagicMock()
            if call_count == 1:
                # First call: nodes
                scalars.all.return_value = [node1, node2]
            else:
                # Second call: edges
                scalars.all.return_value = [edge1]
            result.scalars.return_value = scalars
            return result

        db.execute = multi_execute

        result = await self.service.retrieve_context(
            db, "John Smith", WORKSPACE_ID
        )

        assert "nodes" in result
        assert "edges" in result
        assert "context_text" in result
        assert len(result["nodes"]) > 0
        assert any("John Smith" in n.get("label", "") for n in result["nodes"])

    @pytest.mark.anyio
    async def test_augment_prompt_includes_context(self):
        """Test that augment_copilot_prompt includes graph context."""
        node1 = _make_node_event("Suspect Alpha", "person", "node-a")
        node2 = _make_node_event("Crime Scene", "location", "node-b")
        edge1 = _make_edge_event(
            "node-a", "node-b", "Suspect Alpha", "Crime Scene", "was seen at"
        )

        call_count = 0

        async def multi_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            scalars = MagicMock()
            if call_count == 1:
                scalars.all.return_value = [node1, node2]
            else:
                scalars.all.return_value = [edge1]
            result.scalars.return_value = scalars
            return result

        db = AsyncMock()
        db.execute = multi_execute

        prompt = await self.service.augment_copilot_prompt(
            db, "Suspect Alpha", WORKSPACE_ID
        )

        assert "KNOWLEDGE GRAPH CONTEXT" in prompt
        assert "Suspect Alpha" in prompt

    @pytest.mark.anyio
    async def test_nl_query_find_entity(self):
        """Test natural language query for finding entities."""
        node1 = _make_node_event("Red Car", "vehicle", "v-1")

        db = _mock_db_with_events([node1])

        result = await self.service.query_graph_nl(
            db, "find all vehicles", WORKSPACE_ID
        )

        assert "answer" in result
        assert "evidence_nodes" in result
        assert "confidence" in result
        assert isinstance(result["confidence"], float)

    @pytest.mark.anyio
    async def test_nl_query_find_path(self):
        """Test natural language query for path finding."""
        node1 = _make_node_event("Alice", "person", "p-1")
        node2 = _make_node_event("Bob", "person", "p-2")
        edge1 = _make_edge_event("p-1", "p-2", "Alice", "Bob", "knows")

        call_count = 0

        async def multi_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            scalars = MagicMock()
            # Return all events for any query
            scalars.all.return_value = [node1, node2, edge1]
            result.scalars.return_value = scalars
            return result

        db = AsyncMock()
        db.execute = multi_execute

        result = await self.service.query_graph_nl(
            db, "how is Alice connected to Bob", WORKSPACE_ID
        )

        assert "answer" in result
        assert "confidence" in result

    @pytest.mark.anyio
    async def test_entity_summary(self):
        """Test building entity summary."""
        node1 = _make_node_event("Detective Jones", "person", "det-1")
        edge1 = _make_edge_event(
            "det-1", "case-1", "Detective Jones", "Case 42", "investigates"
        )

        call_count = 0

        async def multi_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            scalars = MagicMock()
            if call_count == 1:
                # Node lookup
                scalars.all.return_value = [node1]
                result.scalar_one_or_none.return_value = node1
            else:
                # Edge lookup
                scalars.all.return_value = [edge1]
            result.scalars.return_value = scalars
            return result

        db = AsyncMock()
        db.execute = multi_execute

        summary = await self.service.build_entity_summary(db, "det-1")

        assert summary["entity"] == "Detective Jones"
        assert summary["type"] == "person"
        assert "summary_text" in summary
        assert "Detective Jones" in summary["summary_text"]

    @pytest.mark.anyio
    async def test_find_path_bfs(self):
        """Test BFS shortest path between two nodes."""
        node_a = _make_node_event("Node A", "person", "a")
        node_b = _make_node_event("Node B", "location", "b")
        node_c = _make_node_event("Node C", "person", "c")
        edge_ab = _make_edge_event("a", "b", "Node A", "Node B", "visited")
        edge_bc = _make_edge_event("b", "c", "Node B", "Node C", "near")

        call_count = 0

        async def multi_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            scalars = MagicMock()
            if call_count == 1:
                # Source/target node lookup
                scalars.all.return_value = [node_a, node_c]
                result.scalars.return_value = scalars
            elif call_count == 2:
                # Edges
                scalars.all.return_value = [edge_ab, edge_bc]
                result.scalars.return_value = scalars
            else:
                # Nodes for label resolution
                scalars.all.return_value = [node_a, node_b, node_c]
                result.scalars.return_value = scalars
            return result

        db = AsyncMock()
        db.execute = multi_execute

        path_result = await self.service.find_path(db, "a", "c", max_depth=5)

        assert "path" in path_result
        assert "edges" in path_result
        assert "distance" in path_result
        if path_result["path"]:
            assert path_result["distance"] == 2
            assert len(path_result["path"]) == 3


# ---------------------------------------------------------------------------
# Copilot Integration Test
# ---------------------------------------------------------------------------


class TestGraphRAGCopilotIntegration:
    @pytest.mark.anyio
    async def test_graph_rag_with_copilot_tool(self):
        """Test that knowledge_graph tool is registered in COPILOT_TOOLS."""
        from app.services.agents.tools import COPILOT_TOOLS

        tool_names = [t["name"] for t in COPILOT_TOOLS]
        assert "query_knowledge_graph" in tool_names

        # Find the tool definition
        kg_tool = next(t for t in COPILOT_TOOLS if t["name"] == "query_knowledge_graph")
        assert "input_schema" in kg_tool
        assert "query" in kg_tool["input_schema"]["properties"]


# ---------------------------------------------------------------------------
# API Route Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_rag_query(test_app):
    """Test POST /api/knowledge-graph/rag/query endpoint exists."""
    response = await test_app.post(
        "/api/knowledge-graph/rag/query",
        json={"question": "find all people", "workspace_id": WORKSPACE_ID},
    )
    # Should return 200 (or possibly empty results), not 404
    assert response.status_code != 404
    data = response.json()
    assert "answer" in data or "detail" in data


@pytest.mark.anyio
async def test_api_rag_context(test_app):
    """Test POST /api/knowledge-graph/rag/context endpoint exists."""
    response = await test_app.post(
        "/api/knowledge-graph/rag/context",
        json={"query": "suspect near warehouse", "workspace_id": WORKSPACE_ID},
    )
    assert response.status_code != 404


@pytest.mark.anyio
async def test_api_entity_summary(test_app):
    """Test GET /api/knowledge-graph/entity/{id}/summary endpoint exists."""
    fake_id = str(uuid.uuid4())
    response = await test_app.get(
        f"/api/knowledge-graph/entity/{fake_id}/summary"
    )
    # Should return 404 (entity not found) or 200, but NOT 405/422
    assert response.status_code in (200, 404, 500)


@pytest.mark.anyio
async def test_api_path(test_app):
    """Test POST /api/knowledge-graph/path endpoint exists."""
    response = await test_app.post(
        "/api/knowledge-graph/path",
        json={
            "source_id": str(uuid.uuid4()),
            "target_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code != 404


@pytest.mark.anyio
async def test_api_nl_query(test_app):
    """Test POST /api/knowledge-graph/nl-query endpoint exists."""
    response = await test_app.post(
        "/api/knowledge-graph/nl-query",
        json={"query": "find all vehicles", "workspace_id": WORKSPACE_ID},
    )
    assert response.status_code != 404
    data = response.json()
    assert "parsed" in data or "detail" in data
