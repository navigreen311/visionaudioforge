"""Durability and scoping for pipeline cron schedules.

Schedules used to live in a per-instance dict. Writes went into the pipeline's
definition JSON but reads came from memory, so after a restart the scheduler
listed no schedules while the rows still existed — it stopped scheduling and
showed nothing to explain why.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.pipeline.scheduler import PipelineScheduler
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_rejects_an_invalid_cron_expression():
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)
    try:
        async with factory() as session:
            with pytest.raises(ValueError, match="Invalid cron expression"):
                await PipelineScheduler().schedule(
                    session, str(uuid4()), "not-a-cron"
                )
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_rescheduling_replaces_rather_than_duplicates():
    """Two rows for one pipeline would fire it twice."""
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)
    scheduler = PipelineScheduler()
    pipeline_id = str(uuid4())

    try:
        async with factory() as session:
            workspace_id = str(await seed_workspace(session, "sched-replace"))
            await scheduler.schedule(
                session, pipeline_id, "0 * * * *", workspace_id=workspace_id
            )
            await scheduler.schedule(
                session, pipeline_id, "30 * * * *", workspace_id=workspace_id
            )
            rows = await scheduler.list_schedules(session, workspace_id)

        assert len(rows) == 1
        assert rows[0]["cron"] == "30 * * * *"
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_schedules_are_scoped_to_their_workspace():
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)
    scheduler = PipelineScheduler()

    try:
        async with factory() as session:
            ours = str(await seed_workspace(session, "sched-ours"))
            theirs = str(await seed_workspace(session, "sched-theirs"))
            await scheduler.schedule(
                session, str(uuid4()), "0 * * * *", workspace_id=ours
            )
            await scheduler.schedule(
                session, str(uuid4()), "0 * * * *", workspace_id=theirs
            )

            mine = await scheduler.list_schedules(session, ours)

        assert len(mine) == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_schedules_survive_a_restart():
    """Write through one engine, read through a brand-new one."""
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)
    scheduler = PipelineScheduler()
    pipeline_id = str(uuid4())

    try:
        async with factory() as session:
            workspace_id = str(await seed_workspace(session, "sched-restart"))
            await scheduler.schedule(
                session, pipeline_id, "*/15 * * * *", workspace_id=workspace_id
            )
    finally:
        await engine.dispose()

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with restarted() as session:
            rows = await scheduler.list_schedules(session, workspace_id)
            upcoming = await scheduler.get_next_runs(session, workspace_id, hours=1)

        assert [r["pipeline_id"] for r in rows] == [pipeline_id]
        assert rows[0]["cron"] == "*/15 * * * *"
        # A schedule that survived must also still produce upcoming runs.
        assert len(upcoming) >= 1
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_disabled_schedules_produce_no_upcoming_runs():
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)
    scheduler = PipelineScheduler()

    try:
        async with factory() as session:
            workspace_id = str(await seed_workspace(session, "sched-disabled"))
            await scheduler.schedule(
                session,
                str(uuid4()),
                "*/5 * * * *",
                enabled=False,
                workspace_id=workspace_id,
            )
            upcoming = await scheduler.get_next_runs(session, workspace_id, hours=1)

        assert upcoming == []
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_unschedule_removes_the_row():
    await requires_postgres()
    engine = await fresh_engine()
    factory = db_session_factory(engine)
    scheduler = PipelineScheduler()

    try:
        async with factory() as session:
            workspace_id = str(await seed_workspace(session, "sched-remove"))
            created = await scheduler.schedule(
                session, str(uuid4()), "0 * * * *", workspace_id=workspace_id
            )

            assert await scheduler.unschedule(session, created["schedule_id"]) is True
            assert await scheduler.list_schedules(session, workspace_id) == []
            # Removing something already gone reports False rather than raising.
            assert await scheduler.unschedule(session, created["schedule_id"]) is False
    finally:
        await engine.dispose()
