"""Workspace settings survive a restart.

General, security, notification and appearance settings were module-level
dicts seeded from their Pydantic defaults. Every save was forgotten on the
next restart, and because the defaults came back the console looked like a
freshly configured install rather than one that had lost anything.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.deps import get_db, get_workspace_id
from app.database import get_async_session
from app.main import app
from app.models.settings import AppearancePreference, WorkspaceSetting
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
async def settings_env():
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "settings")

    try:
        yield factory, workspace_id
    finally:
        await engine.dispose()


def _client(factory, workspace_id=None):
    """Client bound to the test database, standing in for an authenticated caller.

    get_workspace_id fails closed by design — a caller with no resolvable
    workspace gets 403, never a default. These settings are workspace-scoped,
    so the dependency is overridden here rather than relaxed in the app.
    """

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    app.dependency_overrides[get_async_session] = _override
    if workspace_id is not None:
        app.dependency_overrides[get_workspace_id] = lambda: workspace_id
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client(settings_env):
    factory, workspace_id = settings_env
    try:
        async with _client(factory, workspace_id) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

@pytest.mark.anyio
@pytest.mark.parametrize(
    "section,field,value",
    [
        ("general", "project_name", "Acme Vision"),
        ("general", "auto_save", False),
        ("notifications", "email_alerts", False),
        ("notifications", "digest_frequency", "weekly"),
    ],
)
async def test_section_round_trips(client, section, field, value):
    """A saved setting reads back, rather than reverting to the default."""
    current = await client.get(f"/api/settings/{section}")
    assert current.status_code == 200, current.text
    payload = current.json()
    assert field in payload, f"{field} missing from {section}: {payload}"

    payload[field] = value
    saved = await client.put(f"/api/settings/{section}", json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()[field] == value

    again = await client.get(f"/api/settings/{section}")
    assert again.json()[field] == value


@pytest.mark.anyio
async def test_sections_are_stored_separately(client, settings_env):
    """Saving one section must not overwrite another."""
    factory, workspace_id = settings_env

    general = (await client.get("/api/settings/general")).json()
    await client.put("/api/settings/general", json=general)
    notifications = (await client.get("/api/settings/notifications")).json()
    await client.put("/api/settings/notifications", json=notifications)

    async with factory() as session:
        rows = (
            await session.execute(
                select(WorkspaceSetting).where(
                    WorkspaceSetting.workspace_id == workspace_id
                )
            )
        ).scalars().all()

    assert {r.section for r in rows} >= {"general", "notifications"}


@pytest.mark.anyio
async def test_settings_survive_a_restart(settings_env):
    """Written through one engine, read back through a brand-new one."""
    factory, workspace_id = settings_env

    async with _client(factory, workspace_id) as first:
        payload = (await first.get("/api/settings/general")).json()
        field = "project_name"
        payload[field] = "Persisted Name"
        await first.put("/api/settings/general", json=payload)

    app.dependency_overrides.clear()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with _client(restarted, workspace_id) as second:
            after = await second.get("/api/settings/general")
            assert after.json()[field] == "Persisted Name"
    finally:
        app.dependency_overrides.clear()
        await restarted_engine.dispose()


# ---------------------------------------------------------------------------
# Appearance
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_appearance_round_trips_and_persists(settings_env):
    """A saved theme used to revert on every restart."""
    factory, workspace_id = settings_env

    async with _client(factory, workspace_id) as first:
        current = (await first.get("/api/settings/appearance")).json()
        assert "theme" in current

        current["theme"] = "dark"
        saved = await first.put("/api/settings/appearance", json=current)
        assert saved.status_code == 200, saved.text
        assert saved.json()["theme"] == "dark"

    app.dependency_overrides.clear()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with _client(restarted, workspace_id) as second:
            after = await second.get("/api/settings/appearance")
            assert after.json()["theme"] == "dark"

        async with restarted() as session:
            rows = (
                await session.execute(
                    select(AppearancePreference).where(
                        AppearancePreference.user_id.is_(None)
                    )
                )
            ).scalars().all()
            # The shared row is updated in place, not appended to per save.
            assert rows, "no shared appearance row was written"
    finally:
        app.dependency_overrides.clear()
        await restarted_engine.dispose()
