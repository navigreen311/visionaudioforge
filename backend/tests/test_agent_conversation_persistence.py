"""Durability for agent conversations.

Conversation history was a module-level dict pre-seeded with three invented
threads, so a fresh install showed transcripts of troubleshooting sessions
nobody had run, and anything a user actually said was lost on restart.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.conversation import AgentConversation
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
async def agent_client():
    await requires_postgres()

    from app.database import get_async_session
    from app.main import app

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = str(await seed_workspace(session, "agents"))

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = _override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, workspace_id
    finally:
        app.dependency_overrides.pop(get_async_session, None)
        await engine.dispose()


async def _create(client, workspace_id, title="Pipeline question"):
    resp = await client.post(
        "/api/agents/conversations",
        params={"workspace_id": workspace_id},
        json={
            "title": title,
            "agent_id": "agent-alpha",
            "messages": [
                {"role": "user", "content": "Why is it slow?"},
                {"role": "assistant", "content": "Checking."},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.anyio
async def test_a_fresh_install_has_no_conversations(agent_client):
    """The regression: three invented threads used to be pre-seeded."""
    client, workspace_id = agent_client
    resp = await client.get(
        "/api/agents/conversations", params={"workspace_id": workspace_id}
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_messages_round_trip_in_order(agent_client):
    client, workspace_id = agent_client
    created = await _create(client, workspace_id)

    resp = await client.get(f"/api/agents/conversations/{created['id']}")
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "Why is it slow?"


@pytest.mark.anyio
async def test_summary_counts_messages(agent_client):
    client, workspace_id = agent_client
    await _create(client, workspace_id)

    resp = await client.get(
        "/api/agents/conversations", params={"workspace_id": workspace_id}
    )
    assert resp.json()[0]["message_count"] == 2


@pytest.mark.anyio
async def test_unknown_conversation_is_404(agent_client):
    client, _workspace_id = agent_client
    resp = await client.get(
        "/api/agents/conversations/00000000-0000-0000-0000-0000000000ff"
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_conversations_survive_a_restart(agent_client):
    client, workspace_id = agent_client
    created = await _create(client, workspace_id, "Durable thread")

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            stored = (
                await session.execute(
                    select(AgentConversation)
                    .options(selectinload(AgentConversation.messages))
                    .where(AgentConversation.id == created["id"])
                )
            ).scalar_one()

        assert stored.title == "Durable thread"
        assert len(stored.messages) == 2
    finally:
        await restarted_engine.dispose()
