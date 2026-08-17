"""Tests for background work — Celery task lifecycle and dispatch failure.

The failure these guard against is a job that never reaches a terminal state:
the console polls a run that stays "pending" or "running" forever, with
nothing anywhere saying why.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.deps import get_db
from app.main import app
from app.models.pipeline import Pipeline, PipelineRun, PipelineRunStatus
from app.tasks.dispatch import DispatchError, dispatch
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)

# A pipeline the engine can actually run end to end.
SIMPLE_DEFINITION = {
    "nodes": [
        {
            "id": "input_1",
            "type": "input_image",
            "params": {"path": "", "width": 32, "height": 32},
        }
    ],
    "edges": [],
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def task_env():
    """Yield (session_factory, workspace_id, pipeline_id)."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    pipeline_id = uuid.uuid4()
    async with factory() as session:
        workspace_id = await seed_workspace(session, "tasks")
        session.add(
            Pipeline(
                id=pipeline_id,
                workspace_id=workspace_id,
                name="task-pipeline",
                version="1.0",
                definition=SIMPLE_DEFINITION,
                status="active",
            )
        )
        await session.commit()

    try:
        yield factory, workspace_id, pipeline_id
    finally:
        await engine.dispose()


@pytest.fixture
async def client(task_env):
    factory, _, _ = task_env

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# dispatch()
# ---------------------------------------------------------------------------

def test_dispatch_returns_task_id():
    """A queued task's id is handed back to the caller."""
    task = MagicMock()
    task.delay.return_value = MagicMock(id="task-123")

    assert dispatch(task, "arg") == "task-123"
    task.delay.assert_called_once_with("arg")


def test_dispatch_raises_when_broker_is_down():
    """A broker failure is surfaced, not swallowed.

    Both pipeline-run endpoints used to wrap dispatch in `except: pass`, so a
    dead broker produced a run row nobody would ever pick up.
    """
    task = MagicMock()
    task.delay.side_effect = OSError("connection refused")

    with pytest.raises(DispatchError, match="connection refused"):
        dispatch(task)


# ---------------------------------------------------------------------------
# Run lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_task_moves_run_to_completed(task_env):
    """The task records the outcome on the run row the request created."""
    from app.tasks.pipeline import _run_pipeline

    factory, workspace_id, pipeline_id = task_env

    run_id = uuid.uuid4()
    async with factory() as session:
        session.add(
            PipelineRun(
                id=run_id,
                pipeline_id=pipeline_id,
                status=PipelineRunStatus.pending,
            )
        )
        await session.commit()

    result = await _run_pipeline(str(run_id), str(pipeline_id), SIMPLE_DEFINITION, factory)
    assert result["run_id"] == str(run_id)

    async with factory() as session:
        run = (
            await session.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        ).scalar_one()

        # The row reached a terminal state — this is what the console polls.
        assert run.status in (
            PipelineRunStatus.completed,
            PipelineRunStatus.failed,
        )
        assert run.started_at is not None
        assert run.finished_at is not None
        assert run.results is not None


@pytest.mark.anyio
async def test_task_records_failure_on_the_run(task_env):
    """A pipeline that cannot run leaves a failed row, not a hung one."""
    from app.tasks.pipeline import _run_pipeline

    factory, workspace_id, pipeline_id = task_env

    run_id = uuid.uuid4()
    async with factory() as session:
        session.add(
            PipelineRun(
                id=run_id,
                pipeline_id=pipeline_id,
                status=PipelineRunStatus.pending,
            )
        )
        await session.commit()

    broken = {"nodes": [{"id": "n1", "type": "no_such_node_type", "params": {}}], "edges": []}
    result = await _run_pipeline(str(run_id), str(pipeline_id), broken, factory)

    assert result["status"] == "failed"
    assert result["errors"]

    async with factory() as session:
        run = (
            await session.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        ).scalar_one()
        assert run.status == PipelineRunStatus.failed
        assert run.finished_at is not None


@pytest.mark.anyio
async def test_task_loads_definition_when_not_supplied(task_env):
    """Passing only ids works — the task reads the definition from the row."""
    from app.tasks.pipeline import _run_pipeline

    factory, _, pipeline_id = task_env

    run_id = uuid.uuid4()
    async with factory() as session:
        session.add(
            PipelineRun(
                id=run_id,
                pipeline_id=pipeline_id,
                status=PipelineRunStatus.pending,
            )
        )
        await session.commit()

    result = await _run_pipeline(str(run_id), str(pipeline_id), None, factory)
    assert result["run_id"] == str(run_id)


@pytest.mark.anyio
async def test_task_tolerates_a_deleted_run(task_env):
    """A run deleted while queued must not crash the worker."""
    from app.tasks.pipeline import _run_pipeline

    factory, _, pipeline_id = task_env

    result = await _run_pipeline(str(uuid.uuid4()), str(pipeline_id), SIMPLE_DEFINITION, factory)
    assert result["status"] in ("completed", "failed")


# ---------------------------------------------------------------------------
# Endpoint behaviour
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_run_endpoint_queues_and_reports_pending(client, task_env, monkeypatch):
    """A successfully queued run is reported as pending with its row id."""
    factory, _, pipeline_id = task_env

    queued: list[tuple] = []
    monkeypatch.setattr(
        "app.tasks.pipeline.run_pipeline_task.delay",
        lambda *args, **kwargs: queued.append(args) or MagicMock(id="t-1"),
    )

    resp = await client.post(f"/api/pipeline/run/{pipeline_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"

    # The task is handed the run id, so it can report back against that row.
    assert queued and queued[0][0] == str(body["run_id"])


@pytest.mark.anyio
async def test_run_endpoint_marks_run_failed_when_queueing_fails(
    client, task_env, monkeypatch
):
    """With the broker down the run fails immediately instead of hanging."""
    factory, _, pipeline_id = task_env

    def _boom(*args, **kwargs):
        raise OSError("broker unreachable")

    monkeypatch.setattr("app.tasks.pipeline.run_pipeline_task.delay", _boom)

    resp = await client.post(f"/api/pipeline/run/{pipeline_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"

    run_id = uuid.UUID(str(resp.json()["run_id"]))
    async with factory() as session:
        run = (
            await session.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        ).scalar_one()
        assert run.status == PipelineRunStatus.failed
        assert "Could not queue" in run.results["errors"][0]
