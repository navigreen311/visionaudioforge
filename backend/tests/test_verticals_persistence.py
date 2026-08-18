"""Durability and scoping for vertical pack installation.

Install state lived in two module-level dicts that disagreed with each other —
one in the routes, one in services/verticals/installer.py — and both emptied on
restart. A workspace that had installed the Security pack reported nothing
installed after a deploy, while the pack's pipelines and alert presets were
still expected to be in place.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.models.vertical import InstalledVerticalPack
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
async def verticals_client():
    await requires_postgres()

    from app.database import get_async_session
    from app.main import app

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = str(await seed_workspace(session, "verticals"))

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


@pytest.mark.anyio
async def test_nothing_is_installed_on_a_fresh_workspace(verticals_client):
    client, workspace_id, _factory = verticals_client
    resp = await client.get(
        "/api/verticals/installed", params={"workspace_id": workspace_id}
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_install_then_list_reports_the_pack(verticals_client):
    client, workspace_id, _factory = verticals_client

    install = await client.post(
        "/api/verticals/install",
        params={"workspace_id": workspace_id},
        json={"pack_id": "security"},
    )
    assert install.status_code == 200, install.text

    listed = await client.get(
        "/api/verticals/installed", params={"workspace_id": workspace_id}
    )
    assert [p["pack_id"] for p in listed.json()] == ["security"]

    # The browse endpoint reflects it too.
    packs = await client.get(
        "/api/verticals/packs", params={"workspace_id": workspace_id}
    )
    security = next(p for p in packs.json() if p["id"] == "security")
    assert security["installed"] is True


@pytest.mark.anyio
async def test_installing_twice_does_not_duplicate(verticals_client):
    client, workspace_id, _factory = verticals_client
    for _ in range(2):
        resp = await client.post(
            "/api/verticals/install",
            params={"workspace_id": workspace_id},
            json={"pack_id": "security"},
        )
        assert resp.status_code == 200

    listed = await client.get(
        "/api/verticals/installed", params={"workspace_id": workspace_id}
    )
    assert len(listed.json()) == 1


@pytest.mark.anyio
async def test_component_toggles_are_written_back(verticals_client):
    """JSON columns are reassigned, not mutated in place, or nothing persists."""
    client, workspace_id, _factory = verticals_client
    await client.post(
        "/api/verticals/install",
        params={"workspace_id": workspace_id},
        json={"pack_id": "security"},
    )

    listed = (
        await client.get(
            "/api/verticals/installed", params={"workspace_id": workspace_id}
        )
    ).json()[0]
    module = next(iter(listed["enabled_modules"]))

    await client.patch(
        "/api/verticals/install/security",
        params={"workspace_id": workspace_id},
        json={"modules": {module: False}},
    )

    again = (
        await client.get(
            "/api/verticals/installed", params={"workspace_id": workspace_id}
        )
    ).json()[0]
    assert again["enabled_modules"][module] is False


@pytest.mark.anyio
async def test_installs_are_scoped_to_their_workspace(verticals_client):
    client, workspace_id, factory = verticals_client
    async with factory() as session:
        other = str(await seed_workspace(session, "verticals-other"))

    await client.post(
        "/api/verticals/install",
        params={"workspace_id": workspace_id},
        json={"pack_id": "security"},
    )

    theirs = await client.get(
        "/api/verticals/installed", params={"workspace_id": other}
    )
    assert theirs.json() == []


@pytest.mark.anyio
async def test_uninstall_removes_it(verticals_client):
    client, workspace_id, _factory = verticals_client
    await client.post(
        "/api/verticals/install",
        params={"workspace_id": workspace_id},
        json={"pack_id": "security"},
    )

    resp = await client.delete(
        "/api/verticals/install/security", params={"workspace_id": workspace_id}
    )
    assert resp.json()["success"] is True

    listed = await client.get(
        "/api/verticals/installed", params={"workspace_id": workspace_id}
    )
    assert listed.json() == []


@pytest.mark.anyio
async def test_installation_survives_a_restart(verticals_client):
    """The regression: a deploy used to report nothing installed."""
    client, workspace_id, _factory = verticals_client
    await client.post(
        "/api/verticals/install",
        params={"workspace_id": workspace_id},
        json={"pack_id": "security"},
    )

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            rows = (
                await session.execute(
                    select(InstalledVerticalPack).where(
                        InstalledVerticalPack.workspace_id == workspace_id
                    )
                )
            ).scalars().all()

        assert [r.pack_id for r in rows] == ["security"]
        assert rows[0].installed_version is not None
    finally:
        await restarted_engine.dispose()
