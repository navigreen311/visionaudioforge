"""Durability, scoping and honesty for the ReviewOps task queue.

Tasks lived in a module-level dict blended with hardcoded fixtures, so a fresh
install reported eight tasks nobody created, a leaderboard of six reviewers who
did not exist, and a hand-written confusion matrix.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.models.review import ReviewTask
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
async def review_client():
    await requires_postgres()

    from app.database import get_async_session
    from app.main import app

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = str(await seed_workspace(session, "reviewops"))

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


async def _create(client, workspace_id, title="Check batch 12"):
    resp = await client.post(
        "/api/reviewops/tasks",
        json={"title": title, "description": "", "workspace_id": workspace_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.anyio
async def test_an_empty_queue_reports_empty(review_client):
    """The regression: eight fixtures used to be concatenated into this list."""
    client, workspace_id, _factory = review_client
    resp = await client.get(
        "/api/reviewops/tasks", params={"workspace_id": workspace_id}
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_stats_are_counted_not_hardcoded(review_client):
    client, workspace_id, _factory = review_client
    before = await client.get(
        "/api/reviewops/stats", params={"workspace_id": workspace_id}
    )
    assert before.json()["pending"] == 0

    await _create(client, workspace_id)
    await _create(client, workspace_id, "Second")

    after = await client.get(
        "/api/reviewops/stats", params={"workspace_id": workspace_id}
    )
    body = after.json()
    assert body["pending"] == 2
    # Deltas have no stored history; null says unknown rather than "no change".
    assert body["pending_delta"] is None


@pytest.mark.anyio
async def test_leaderboard_and_quality_do_not_invent_people_or_scores(review_client):
    client, workspace_id, _factory = review_client

    leaderboard = await client.get(
        "/api/reviewops/leaderboard", params={"workspace_id": workspace_id}
    )
    assert leaderboard.json() == []

    quality = await client.get(
        "/api/reviewops/quality", params={"workspace_id": workspace_id}
    )
    body = quality.json()
    assert body["supported"] is False
    assert body["confusion_matrix"] == []
    assert body["overall_accuracy"] is None


@pytest.mark.anyio
async def test_assign_then_complete_flows_through_to_the_leaderboard(review_client):
    client, workspace_id, _factory = review_client
    task = await _create(client, workspace_id)

    assigned = await client.post(
        f"/api/reviewops/tasks/{task['id']}/assign",
        json={"reviewer_id": "alice"},
    )
    assert assigned.json()["status"] == "assigned"

    await client.post(
        f"/api/reviewops/tasks/{task['id']}/review",
        json={"verdict": "approved"},
    )

    leaderboard = await client.get(
        "/api/reviewops/leaderboard", params={"workspace_id": workspace_id}
    )
    entry = leaderboard.json()[0]
    assert entry["reviewer_id"] == "alice"
    assert entry["reviews_completed"] == 1
    # Nothing measures these, so they must stay null rather than be filled in.
    assert entry["accuracy"] is None


@pytest.mark.anyio
async def test_auto_assign_actually_assigns(review_client):
    """It used to report 12 assignments without touching anything."""
    client, workspace_id, _factory = review_client

    empty = await client.post(
        "/api/reviewops/auto-assign", params={"workspace_id": workspace_id}
    )
    assert empty.json()["assignments_made"] == 0

    seed = await _create(client, workspace_id, "Seed")
    await client.post(
        f"/api/reviewops/tasks/{seed['id']}/assign", json={"reviewer_id": "bob"}
    )
    await _create(client, workspace_id, "Pending one")
    await _create(client, workspace_id, "Pending two")

    resp = await client.post(
        "/api/reviewops/auto-assign", params={"workspace_id": workspace_id}
    )
    assert resp.json()["assignments_made"] == 2

    listed = await client.get(
        "/api/reviewops/tasks", params={"workspace_id": workspace_id, "status": "assigned"}
    )
    assert len(listed.json()) == 3


@pytest.mark.anyio
async def test_tasks_are_scoped_to_their_workspace(review_client):
    client, workspace_id, factory = review_client
    async with factory() as session:
        other = str(await seed_workspace(session, "reviewops-other"))

    await _create(client, workspace_id, "Ours")
    await _create(client, other, "Theirs")

    resp = await client.get(
        "/api/reviewops/tasks", params={"workspace_id": workspace_id}
    )
    assert [t["title"] for t in resp.json()] == ["Ours"]


@pytest.mark.anyio
async def test_unknown_task_is_404(review_client):
    client, _workspace_id, _factory = review_client
    resp = await client.get(
        "/api/reviewops/tasks/00000000-0000-0000-0000-0000000000ff"
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_tasks_survive_a_restart(review_client):
    client, workspace_id, _factory = review_client
    task = await _create(client, workspace_id, "Durable task")

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            stored = (
                await session.execute(
                    select(ReviewTask).where(ReviewTask.id == task["id"])
                )
            ).scalar_one()
        assert stored.title == "Durable task"
    finally:
        await restarted_engine.dispose()
