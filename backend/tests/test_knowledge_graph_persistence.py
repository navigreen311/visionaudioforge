"""Durability, scoping and honesty for the knowledge graph routes.

Nodes and edges were module-level dicts, and every read path had a fabricated
fallback: an unknown id returned a "Mock Node", an empty graph returned three
invented edges, and search always reported three hits. A graph that answers
confidently about entities it does not have is worse than one that returns
nothing.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

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
async def graph_client():
    """Client whose knowledge-graph routes read the test database."""
    await requires_postgres()

    from app.database import get_async_session
    from app.main import app

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = str(await seed_workspace(session, "kg"))

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, workspace_id, factory
    finally:
        app.dependency_overrides.pop(get_async_session, None)
        await engine.dispose()


async def _create_node(client, workspace_id, label, node_type="entity"):
    resp = await client.post(
        "/api/knowledge-graph/nodes",
        json={
            "label": label,
            "node_type": node_type,
            "properties": {},
            "workspace_id": workspace_id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.anyio
async def test_unknown_node_is_a_404_not_an_invented_one(graph_client):
    """The regression this rewrite exists for."""
    client, _workspace_id, _factory = graph_client
    resp = await client.get(
        "/api/knowledge-graph/nodes/00000000-0000-0000-0000-0000000000ff"
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_search_reports_no_matches_as_empty(graph_client):
    client, workspace_id, _factory = graph_client
    resp = await client.get(
        "/api/knowledge-graph/search",
        params={"q": "nothing-matches-this", "workspace_id": workspace_id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["matching_node_ids"] == []


@pytest.mark.anyio
async def test_edges_for_a_node_with_none_returns_empty(graph_client):
    client, workspace_id, _factory = graph_client
    node_id = await _create_node(client, workspace_id, "Lonely")

    resp = await client.get(f"/api/knowledge-graph/nodes/{node_id}/edges")
    assert resp.status_code == 200
    assert resp.json() == {"node_id": node_id, "edges": [], "total": 0}


@pytest.mark.anyio
async def test_edge_to_a_missing_node_is_rejected(graph_client):
    """An edge to a node that was never created is a dangling claim."""
    client, workspace_id, _factory = graph_client
    node_id = await _create_node(client, workspace_id, "Real")

    resp = await client.post(
        "/api/knowledge-graph/edges",
        json={
            "source_id": node_id,
            "target_id": "00000000-0000-0000-0000-0000000000ff",
            "relation": "knows",
            "workspace_id": workspace_id,
        },
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_nodes_are_scoped_to_their_workspace(graph_client):
    client, workspace_id, factory = graph_client
    async with factory() as session:
        other = str(await seed_workspace(session, "kg-other"))

    await _create_node(client, workspace_id, "Ours")
    await _create_node(client, other, "Theirs")

    resp = await client.get(
        "/api/knowledge-graph/nodes", params={"workspace_id": workspace_id}
    )
    assert [n["label"] for n in resp.json()] == ["Ours"]


@pytest.mark.anyio
async def test_path_reports_when_no_path_exists(graph_client):
    client, workspace_id, _factory = graph_client
    a = await _create_node(client, workspace_id, "A")
    b = await _create_node(client, workspace_id, "B")

    resp = await client.get(
        "/api/knowledge-graph/path", params={"from": a, "to": b}
    )
    body = resp.json()
    assert body["found"] is False
    assert body["path"] == []


@pytest.mark.anyio
async def test_path_finds_a_real_route(graph_client):
    client, workspace_id, _factory = graph_client
    a = await _create_node(client, workspace_id, "A")
    b = await _create_node(client, workspace_id, "B")
    c = await _create_node(client, workspace_id, "C")

    for source, target in ((a, b), (b, c)):
        resp = await client.post(
            "/api/knowledge-graph/edges",
            json={
                "source_id": source,
                "target_id": target,
                "relation": "next",
                "workspace_id": workspace_id,
            },
        )
        assert resp.status_code == 201, resp.text

    resp = await client.get("/api/knowledge-graph/path", params={"from": a, "to": c})
    body = resp.json()
    assert body["found"] is True
    assert body["hops"] == 2
    assert [step["node_id"] for step in body["path"]] == [a, b, c]


@pytest.mark.anyio
async def test_graph_survives_a_restart(graph_client):
    """Write through the API, read through a brand-new engine."""
    client, workspace_id, _factory = graph_client
    node_id = await _create_node(client, workspace_id, "Durable Entity", "person")

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        from sqlalchemy import select

        from app.models.graph_node import GraphNode

        async with restarted() as session:
            stored = (
                await session.execute(
                    select(GraphNode).where(GraphNode.id == node_id)
                )
            ).scalar_one()

        assert stored.label == "Durable Entity"
        assert stored.node_type == "person"
    finally:
        await restarted_engine.dispose()
