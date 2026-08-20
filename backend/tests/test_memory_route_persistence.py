"""The /api/memory route module's own state, now in semantic_memories.

This module kept a dict of memories beside the semantic_memories table. A
memory created through POST /api/memory went into the dict, so it vanished on
restart — and /search and /timeline, which already read the table, never saw
it even while the process was alive.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_db, get_workspace_id
from app.main import app
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
async def memory_env():
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "memory-route")

    try:
        yield factory, workspace_id
    finally:
        await engine.dispose()


def _client(factory, workspace_id):
    """Client standing in for a caller authenticated to *workspace_id*."""

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    app.dependency_overrides[get_workspace_id] = lambda: workspace_id
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client(memory_env):
    factory, workspace_id = memory_env
    try:
        async with _client(factory, workspace_id) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


async def _create(client, content="a memory", **kwargs):
    payload = {"content": content, "category": "fact", "importance": 0.7}
    payload.update(kwargs)
    resp = await client.post("/api/memory", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_create_returns_a_real_id(client):
    """The id is a row id, not a mem-xxxxxxxx string from a dict key."""
    created = await _create(client, "CLIP aligns image and text")

    assert uuid.UUID(created["id"])
    assert created["content"] == "CLIP aligns image and text"
    assert created["importance_score"] == 0.7

    fetched = await client.get(f"/api/memory/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["content"] == "CLIP aligns image and text"


@pytest.mark.anyio
async def test_created_memory_is_visible_to_search(client):
    """The bug this conversion fixes: /search reads the table, create wrote a dict."""
    await _create(client, "a distinctive phrase about faiss")

    found = await client.get("/api/memory/search", params={"q": "distinctive"})
    assert found.status_code == 200
    assert any("distinctive" in m["content"] for m in found.json())


@pytest.mark.anyio
async def test_update_and_delete(client):
    created = await _create(client)

    patched = await client.patch(
        f"/api/memory/{created['id']}", json={"content": "edited", "importance": 0.9}
    )
    assert patched.status_code == 200
    assert patched.json()["content"] == "edited"
    assert patched.json()["importance_score"] == 0.9

    deleted = await client.delete(f"/api/memory/{created['id']}")
    assert deleted.status_code == 200

    assert (await client.get(f"/api/memory/{created['id']}")).status_code == 404


@pytest.mark.anyio
async def test_unknown_and_malformed_ids_404(client):
    assert (await client.get(f"/api/memory/{uuid.uuid4()}")).status_code == 404
    assert (await client.get("/api/memory/mem-00000001")).status_code == 404


# ---------------------------------------------------------------------------
# Recall and summary
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_recall_filters(client):
    await _create(client, "public fact", category="fact", importance=0.9)
    await _create(client, "private note", category="note", importance=0.9, is_private=True)

    public_only = await client.post("/api/memory/recall", json={"query": "", "k": 10})
    assert public_only.status_code == 200
    assert all(not m["is_private"] for m in public_only.json())

    with_private = await client.post(
        "/api/memory/recall", json={"query": "", "k": 10, "include_private": True}
    )
    assert any(m["is_private"] for m in with_private.json())

    by_category = await client.post(
        "/api/memory/recall", json={"query": "", "k": 10, "category": "fact"}
    )
    assert {m["category"] for m in by_category.json()} == {"fact"}


@pytest.mark.anyio
async def test_summary_counts_real_rows(client):
    """total was floored at 24 and the histogram was ten hardcoded numbers."""
    empty = await client.get("/api/memory/summary")
    assert empty.json()["total"] == 0
    assert sum(empty.json()["importance_histogram"]) == 0

    await _create(client, "one", importance=0.9)
    await _create(client, "two", importance=0.2)

    summary = (await client.get("/api/memory/summary")).json()
    assert summary["total"] == 2
    assert sum(summary["importance_histogram"]) == 2
    assert summary["high_importance_count"] == 1


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_decay_all_reports_what_it_changed(client):
    """memories_affected was floored at 5, so an empty workspace reported work."""
    empty = await client.post("/api/memory/decay-all")
    assert empty.json()["memories_affected"] == 0

    await _create(client, "decays", importance=0.8)
    after = await client.post("/api/memory/decay-all")
    assert after.json()["memories_affected"] == 1


@pytest.mark.anyio
async def test_decay_history_records_each_step(client):
    created = await _create(client, "tracked", importance=0.8)

    await client.post(f"/api/memory/{created['id']}/decay")
    await client.post(f"/api/memory/{created['id']}/decay")

    history = await client.get(f"/api/memory/{created['id']}/decay-history")
    assert history.status_code == 200
    body = history.json()

    assert body["initial_importance"] == 0.8
    assert len(body["events"]) == 2
    assert body["current_importance"] < 0.8
    assert body["events"][0]["importance_before"] == 0.8


@pytest.mark.anyio
async def test_promote_and_demote(client):
    created = await _create(client, "moves", importance=0.5)

    promoted = await client.post(f"/api/memory/{created['id']}/promote")
    assert promoted.json()["importance_score"] == 0.6

    demoted = await client.post(f"/api/memory/demote/{created['id']}")
    assert demoted.json()["importance_score"] == 0.5


# ---------------------------------------------------------------------------
# Scoping and durability
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_memories_are_workspace_scoped(memory_env):
    """One workspace's memories must not appear in another's."""
    factory, workspace_id = memory_env

    async with factory() as session:
        other = await seed_workspace(session, "memory-other")

    async with _client(factory, workspace_id) as mine:
        created = await _create(mine, "mine only")
    app.dependency_overrides.clear()

    try:
        async with _client(factory, other) as theirs:
            listed = await theirs.post("/api/memory/recall", json={"query": "", "k": 50})
            assert listed.json() == []
            assert (await theirs.get(f"/api/memory/{created['id']}")).status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_memory_survives_a_restart(memory_env):
    """Written through one engine, read back through a brand-new one."""
    factory, workspace_id = memory_env

    async with _client(factory, workspace_id) as first:
        created = await _create(first, "durable memory", importance=0.6)
        await first.post(f"/api/memory/{created['id']}/decay")
    app.dependency_overrides.clear()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with _client(restarted, workspace_id) as second:
            fetched = await second.get(f"/api/memory/{created['id']}")
            assert fetched.status_code == 200
            assert fetched.json()["content"] == "durable memory"

            history = await second.get(f"/api/memory/{created['id']}/decay-history")
            assert len(history.json()["events"]) == 1

            exported = await second.post("/api/memory/export")
            assert exported.json()["count"] == 1
    finally:
        app.dependency_overrides.clear()
        await restarted_engine.dispose()
