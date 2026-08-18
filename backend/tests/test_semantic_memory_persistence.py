"""Durability and scoping for semantic memories.

Memories were a module-level dict: user-authored knowledge the platform
promised to remember and then lost on every restart, with nothing to indicate
anything had been forgotten.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.models.semantic_memory import SemanticMemory
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
async def memory_client():
    await requires_postgres()

    from app.database import get_async_session
    from app.main import app

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = str(await seed_workspace(session, "memory"))

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


async def _store(client, workspace_id, content, importance=0.5, category="general"):
    resp = await client.post(
        "/api/semantic-memory/store",
        json={
            "content": content,
            "category": category,
            "importance": importance,
            "workspace_id": workspace_id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.anyio
async def test_storing_without_a_workspace_is_rejected(memory_client):
    client, _workspace_id, _factory = memory_client
    resp = await client.post(
        "/api/semantic-memory/store", json={"content": "orphan"}
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_memories_are_scoped_to_their_workspace(memory_client):
    client, workspace_id, factory = memory_client
    async with factory() as session:
        other = str(await seed_workspace(session, "memory-other"))

    await _store(client, workspace_id, "ours")
    await _store(client, other, "theirs")

    resp = await client.get(
        "/api/semantic-memory/memories", params={"workspace_id": workspace_id}
    )
    assert [m["content"] for m in resp.json()] == ["ours"]


@pytest.mark.anyio
async def test_recall_records_the_access(memory_client):
    """Decay and promotion are only meaningful if usage is real."""
    client, workspace_id, _factory = memory_client
    await _store(client, workspace_id, "the cat sat on the mat")

    resp = await client.post(
        "/api/semantic-memory/recall",
        json={"query": "cat", "workspace_id": workspace_id},
    )
    body = resp.json()
    assert body["total"] == 1
    assert body["method"] == "substring_match"

    listed = await client.get(
        "/api/semantic-memory/memories", params={"workspace_id": workspace_id}
    )
    assert listed.json()[0]["access_count"] == 1


@pytest.mark.anyio
async def test_recall_reports_no_matches_honestly(memory_client):
    client, workspace_id, _factory = memory_client
    await _store(client, workspace_id, "something unrelated")

    resp = await client.post(
        "/api/semantic-memory/recall",
        json={"query": "nothing-matches", "workspace_id": workspace_id},
    )
    assert resp.json()["total"] == 0
    assert resp.json()["results"] == []


@pytest.mark.anyio
async def test_promote_and_decay_change_importance(memory_client):
    client, workspace_id, _factory = memory_client
    stored = await _store(client, workspace_id, "important thing", importance=0.5)

    promoted = await client.post(
        f"/api/semantic-memory/promote/{stored['id']}", params={"boost": 0.2}
    )
    assert promoted.json()["importance"] == pytest.approx(0.7)

    decayed = await client.post(
        "/api/semantic-memory/decay",
        params={"threshold": 0.1, "factor": 0.5, "workspace_id": workspace_id},
    )
    assert decayed.json()["decayed_count"] == 1

    listed = await client.get(
        "/api/semantic-memory/memories", params={"workspace_id": workspace_id}
    )
    assert listed.json()[0]["importance"] == pytest.approx(0.35)


@pytest.mark.anyio
async def test_promoting_an_unknown_memory_is_404(memory_client):
    client, _workspace_id, _factory = memory_client
    resp = await client.post(
        "/api/semantic-memory/promote/00000000-0000-0000-0000-0000000000ff"
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_memories_survive_a_restart(memory_client):
    """Write through the API, read through a brand-new engine."""
    client, workspace_id, _factory = memory_client
    stored = await _store(client, workspace_id, "remember me", importance=0.9)

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            row = (
                await session.execute(
                    select(SemanticMemory).where(SemanticMemory.id == stored["id"])
                )
            ).scalar_one()

        assert row.content == "remember me"
        assert row.importance == pytest.approx(0.9)
    finally:
        await restarted_engine.dispose()
