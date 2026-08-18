"""Helpers for tests that need a real database.

CI runs pytest without a Postgres service, so every DB-backed test must skip
rather than fail when no server is reachable. Import :func:`db_session_factory`
and :func:`requires_postgres` instead of hand-rolling that check.

Point the tests at a server with the usual settings, e.g.::

    POSTGRES_HOST=localhost POSTGRES_USER=vaf POSTGRES_PASSWORD=test \
    POSTGRES_DB=vaf_ws_b_test pytest backend/tests/ -v
"""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base

# Import every model module so Base.metadata knows the full schema before
# create_all runs. Without this, tables are silently missing.
import app.models  # noqa: F401


def database_url() -> str:
    """Return the URL tests should connect to.

    The database name falls back to POSTGRES_DB before the historical
    `vaf_ws_b_test`. CI creates only POSTGRES_DB and never sets
    POSTGRES_TEST_DB, so every test guarded by `requires_postgres` — 67 of
    them, including the whole restart-survival suite — found nothing to
    connect to and skipped. Skips are green, so this looked like a passing
    build for as long as it had been true.
    """
    if url := os.getenv("TEST_DATABASE_URL"):
        return url

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "vaf")
    password = os.getenv("POSTGRES_PASSWORD", "test")
    name = (
        os.getenv("POSTGRES_TEST_DB")
        or os.getenv("POSTGRES_DB")
        or "vaf_ws_b_test"
    )
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


_available: bool | None = None


async def postgres_available() -> bool:
    """Check once whether the test database can be reached."""
    global _available
    if _available is not None:
        return _available

    engine = create_async_engine(database_url())
    try:
        async with engine.connect():
            pass
        _available = True
    except Exception:
        _available = False
    finally:
        await engine.dispose()
    return _available


async def requires_postgres() -> None:
    """Skip the calling test unless a database is reachable."""
    if not await postgres_available():
        pytest.skip(f"no database reachable at {database_url()}")


async def fresh_engine(**kwargs: Any):
    """Create an engine with the schema present.

    ``create_all`` is idempotent, so repeated calls across tests are cheap.
    """
    engine = create_async_engine(database_url(), **kwargs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


def db_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """Build a session factory that does not expire objects on commit."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed_workspace(session: AsyncSession, name: str = "test-workspace"):
    """Insert a workspace and return its id.

    Most tables carry a ``workspace_id`` foreign key, so rows cannot be written
    without one.
    """
    from app.models.workspace import Workspace

    workspace = Workspace(
        id=uuid4(),
        name=name,
        slug=f"{name}-{uuid4().hex[:8]}",
    )
    session.add(workspace)
    await session.commit()
    return workspace.id
