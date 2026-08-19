"""The session-level workspace filter, proved directly.

``test_tenant_isolation.py`` proves isolation through the HTTP surface, route by
route. That is the right test, and it does not scale: there are 191 by-id routes
and 185 of them had no owner check, so proving each one individually would take
185 tests to say one thing.

This file proves the mechanism instead. If ``app/core/tenancy.py`` confines every
ORM read to the caller's workspace, then a route that forgets to filter returns
nothing rather than another tenant's row - and that holds for routes nobody has
written yet.

Both files earn their place: this one proves the floor, the other proves the
floor is actually under the routes people call.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.tenancy import (
    EXEMPT_TABLES,
    current_workspace,
    set_current_workspace,
    reset_current_workspace,
    unscoped,
)
from app.database import async_session_factory
from app.models.agent import Agent, AgentMemory
from app.models.alert import Alert, AlertRule, AlertSeverity, AlertStatus
from app.models.asset import Asset
from app.models.dataset import Dataset
from app.models.evidence import EvidenceBundle
from app.models.workspace import Workspace

pytestmark = pytest.mark.anyio

WORKSPACE_A = uuid.UUID("aaaaaaaa-0000-0000-0000-00000000000a")
WORKSPACE_B = uuid.UUID("bbbbbbbb-0000-0000-0000-00000000000b")


@pytest.fixture
async def two_workspaces():
    """Two real workspace rows, cleaned up afterwards.

    Created under `unscoped()` because workspaces are exempt from the filter and
    this is setup, not a query under test.
    """
    async with async_session_factory() as db:
        with unscoped():
            for ws_id, name in ((WORKSPACE_A, "scoping-a"), (WORKSPACE_B, "scoping-b")):
                existing = await db.get(Workspace, ws_id)
                if existing is None:
                    db.add(Workspace(id=ws_id, name=name, slug=f"{name}-{uuid.uuid4().hex[:8]}"))
            await db.commit()
    yield WORKSPACE_A, WORKSPACE_B


def _row_factories():
    """(label, model, builder) for the families the audit called out by name."""
    return [
        (
            "alert rule",
            AlertRule,
            lambda ws: AlertRule(
                name="scoping probe", conditions={}, actions={}, workspace_id=ws
            ),
        ),
        (
            "agent",
            Agent,
            lambda ws: Agent(name="scoping probe", agent_type="copilot", workspace_id=ws),
        ),
        (
            "dataset",
            Dataset,
            lambda ws: Dataset(name="scoping probe", modality="image", workspace_id=ws),
        ),
        (
            "asset",
            Asset,
            lambda ws: Asset(
                type="image",
                path="scoping/probe.png",
                filename="probe.png",
                size_bytes=1,
                workspace_id=ws,
            ),
        ),
        (
            "evidence bundle",
            EvidenceBundle,
            lambda ws: EvidenceBundle(
                alert_id="probe",
                alert_snapshot={},
                bundle_metadata={},
                workspace_id=ws,
            ),
        ),
    ]


@pytest.mark.parametrize(
    "label,model,build", _row_factories(), ids=[f[0] for f in _row_factories()]
)
async def test_a_row_is_invisible_from_another_workspace(
    two_workspaces, label, model, build
):
    ws_a, ws_b = two_workspaces

    async with async_session_factory() as db:
        with unscoped():  # setup, not the query under test
            row = build(ws_a)
            db.add(row)
            await db.commit()
            row_id = row.id

    # As B: the row must be invisible both by id and in a list.
    async with async_session_factory() as db:
        token = set_current_workspace(ws_b)
        try:
            assert await db.get(model, row_id) is None, (
                f"tenant isolation breached: B loaded A's {label} by id"
            )
            found = (await db.execute(select(model).where(model.id == row_id))).scalars().all()
            assert found == [], f"tenant isolation breached: B selected A's {label}"
        finally:
            reset_current_workspace(token)

    # As A: still perfectly readable, or the filter is just breaking everything.
    async with async_session_factory() as db:
        token = set_current_workspace(ws_a)
        try:
            assert await db.get(model, row_id) is not None, (
                f"the filter hid A's own {label} from A"
            )
        finally:
            reset_current_workspace(token)


async def test_no_tenant_context_does_not_filter(two_workspaces):
    """Login, registration and workers run without a tenant and must still read."""
    ws_a, _ = two_workspaces
    async with async_session_factory() as db:
        with unscoped():
            agent = Agent(name="no-context probe", agent_type="copilot", workspace_id=ws_a)
            db.add(agent)
            await db.commit()
            agent_id = agent.id

    assert current_workspace.get() is None
    async with async_session_factory() as db:
        assert await db.get(Agent, agent_id) is not None


async def test_unscoped_widens_only_inside_the_block(two_workspaces):
    ws_a, ws_b = two_workspaces
    async with async_session_factory() as db:
        with unscoped():
            row = AlertRule(name="unscoped probe", conditions={}, actions={}, workspace_id=ws_a)
            db.add(row)
            await db.commit()
            row_id = row.id

    async with async_session_factory() as db:
        token = set_current_workspace(ws_b)
        try:
            with unscoped():
                assert await db.get(AlertRule, row_id) is not None, (
                    "unscoped() did not widen the query"
                )
            db.expunge_all()
            assert await db.get(AlertRule, row_id) is None, (
                "the widening leaked past the unscoped() block"
            )
        finally:
            reset_current_workspace(token)


async def test_a_child_row_is_scoped_through_its_parent(two_workspaces):
    """AgentMemory has no workspace_id of its own.

    It belongs to a tenant through its Agent, and the filter scopes it by that
    foreign key rather than requiring a migration to duplicate the column. This
    is the case that covers agent memories, pipeline runs, experiment epochs,
    evidence bundle items and annotations - 23 classes in all.
    """
    ws_a, ws_b = two_workspaces
    async with async_session_factory() as db:
        with unscoped():
            agent = Agent(name="memory owner", agent_type="copilot", workspace_id=ws_a)
            db.add(agent)
            await db.flush()
            memory = AgentMemory(agent_id=agent.id, content="tenant A private note")
            db.add(memory)
            await db.commit()
            memory_id = memory.id

    async with async_session_factory() as db:
        token = set_current_workspace(ws_b)
        try:
            assert await db.get(AgentMemory, memory_id) is None, (
                "tenant isolation breached: B read A's agent memory"
            )
        finally:
            reset_current_workspace(token)


async def test_alerts_are_scoped(two_workspaces):
    """Alerts hang off a rule; both carry workspace_id and both must be scoped."""
    ws_a, ws_b = two_workspaces
    async with async_session_factory() as db:
        with unscoped():
            rule = AlertRule(name="alert rule", conditions={}, actions={}, workspace_id=ws_a)
            db.add(rule)
            await db.flush()
            alert = Alert(
                rule_id=rule.id,
                severity=AlertSeverity.high,
                status=AlertStatus.new,
                workspace_id=ws_a,
            )
            db.add(alert)
            await db.commit()
            alert_id = alert.id

    async with async_session_factory() as db:
        token = set_current_workspace(ws_b)
        try:
            assert await db.get(Alert, alert_id) is None, (
                "tenant isolation breached: B read A's alert"
            )
        finally:
            reset_current_workspace(token)


def test_the_exemptions_are_the_ones_we_meant():
    """A guard on the escape hatch itself.

    Adding a table here makes it readable across every tenant. That should be a
    deliberate, reviewed act, not something that drifts in - so the list is
    pinned, and widening it means changing this test on purpose.
    """
    assert EXEMPT_TABLES == frozenset({"users", "workspaces", "audit_logs"})


# ---------------------------------------------------------------------------
# The write path
# ---------------------------------------------------------------------------
#
# Everything above proves a read cannot cross tenants. A bulk `update()` or
# `delete()` never loads a row, so none of it applies: the filter above hangs
# off `execute_state.is_select`. A statement that mutates by id alone reached
# the database with nothing standing in front of it.
#
# Same shape as the read tests, deliberately: if the mechanism covers writes
# then these are a verification of it rather than six hand-patched files.


def _write_probes():
    """(label, model, builder, column, new value) for bulk-write probes.

    Separate from `_row_factories()` rather than an extra tuple element, so the
    read tests above keep their shape and their ids.
    """
    return [
        ("alert rule", AlertRule,
         lambda ws: AlertRule(name="write probe", conditions={}, actions={}, workspace_id=ws),
         "name", "MUTATED BY TENANT B"),
        ("agent", Agent,
         lambda ws: Agent(name="write probe", agent_type="copilot", workspace_id=ws),
         "name", "MUTATED BY TENANT B"),
        ("dataset", Dataset,
         lambda ws: Dataset(name="write probe", modality="image", workspace_id=ws),
         "name", "MUTATED BY TENANT B"),
        ("asset", Asset,
         lambda ws: Asset(type="image", path="write/probe.png", filename="probe.png",
                          size_bytes=1, workspace_id=ws),
         "filename", "mutated-by-b.png"),
    ]


_WRITE_IDS = [p[0] for p in _write_probes()]


async def _insert_as(ws, build):
    async with async_session_factory() as db:
        with unscoped():  # setup, not the statement under test
            row = build(ws)
            db.add(row)
            await db.commit()
            return row.id


async def _read_unscoped(model, row_id):
    async with async_session_factory() as db:
        with unscoped():
            return await db.get(model, row_id)


@pytest.mark.parametrize("label,model,build,column,new_value", _write_probes(), ids=_WRITE_IDS)
async def test_bulk_update_cannot_touch_another_workspace(
    two_workspaces, label, model, build, column, new_value
):
    """Tenant B issuing `update().where(id == A's id)` must change nothing."""
    from sqlalchemy import update

    ws_a, ws_b = two_workspaces
    row_id = await _insert_as(ws_a, build)
    original = getattr(await _read_unscoped(model, row_id), column)

    async with async_session_factory() as db:
        token = set_current_workspace(ws_b)
        try:
            await db.execute(
                update(model)
                .where(model.id == row_id)
                .values(**{column: new_value})
                .execution_options(synchronize_session=False)
            )
            await db.commit()
        finally:
            reset_current_workspace(token)

    after = getattr(await _read_unscoped(model, row_id), column)
    assert after == original, (
        f"tenant isolation breached: B's bulk UPDATE rewrote A's {label} "
        f"({original!r} -> {after!r})"
    )


@pytest.mark.parametrize("label,model,build,column,new_value", _write_probes(), ids=_WRITE_IDS)
async def test_bulk_delete_cannot_touch_another_workspace(
    two_workspaces, label, model, build, column, new_value
):
    """Tenant B issuing `delete().where(id == A's id)` must delete nothing."""
    from sqlalchemy import delete

    ws_a, ws_b = two_workspaces
    row_id = await _insert_as(ws_a, build)

    async with async_session_factory() as db:
        token = set_current_workspace(ws_b)
        try:
            await db.execute(
                delete(model)
                .where(model.id == row_id)
                .execution_options(synchronize_session=False)
            )
            await db.commit()
        finally:
            reset_current_workspace(token)

    assert await _read_unscoped(model, row_id) is not None, (
        f"tenant isolation breached: B's bulk DELETE removed A's {label}"
    )


@pytest.mark.parametrize("label,model,build,column,new_value", _write_probes(), ids=_WRITE_IDS)
async def test_a_workspace_can_still_write_its_own_rows(
    two_workspaces, label, model, build, column, new_value
):
    """The other half. A filter that blocks everything is not isolation."""
    from sqlalchemy import delete, update

    ws_a, _ = two_workspaces
    row_id = await _insert_as(ws_a, build)

    async with async_session_factory() as db:
        token = set_current_workspace(ws_a)
        try:
            await db.execute(
                update(model)
                .where(model.id == row_id)
                .values(**{column: new_value})
                .execution_options(synchronize_session=False)
            )
            await db.commit()
        finally:
            reset_current_workspace(token)

    assert getattr(await _read_unscoped(model, row_id), column) == new_value, (
        f"A could not update its own {label}"
    )

    async with async_session_factory() as db:
        token = set_current_workspace(ws_a)
        try:
            await db.execute(
                delete(model)
                .where(model.id == row_id)
                .execution_options(synchronize_session=False)
            )
            await db.commit()
        finally:
            reset_current_workspace(token)

    assert await _read_unscoped(model, row_id) is None, (
        f"A could not delete its own {label}"
    )


async def test_bulk_write_to_a_child_row_is_scoped_through_its_parent(two_workspaces):
    """The correlated-subquery case, on the write path.

    AgentMemory has no workspace_id; it is scoped by an IN against its parent
    Agent. That criteria composes into a SELECT easily enough - whether it
    survives being attached to an UPDATE or DELETE is the question this asks,
    and it covers the 23 child classes that have no column of their own.
    """
    from sqlalchemy import delete, update

    ws_a, ws_b = two_workspaces
    async with async_session_factory() as db:
        with unscoped():
            agent = Agent(name="child write owner", agent_type="copilot", workspace_id=ws_a)
            db.add(agent)
            await db.flush()
            memory = AgentMemory(agent_id=agent.id, content="tenant A private note")
            db.add(memory)
            await db.commit()
            memory_id = memory.id

    async with async_session_factory() as db:
        token = set_current_workspace(ws_b)
        try:
            await db.execute(
                update(AgentMemory).where(AgentMemory.id == memory_id)
                .values(content="MUTATED BY B")
                .execution_options(synchronize_session=False)
            )
            await db.execute(
                delete(AgentMemory).where(AgentMemory.id == memory_id)
                .execution_options(synchronize_session=False)
            )
            await db.commit()
        finally:
            reset_current_workspace(token)

    survivor = await _read_unscoped(AgentMemory, memory_id)
    assert survivor is not None, "B's bulk DELETE removed A's agent memory"
    assert survivor.content == "tenant A private note", (
        "B's bulk UPDATE rewrote A's agent memory"
    )


async def test_an_exempt_table_is_still_writable(two_workspaces):
    """audit_logs must stay writable from any context, including none.

    The audit middleware records failed logins, which by definition have no
    tenant. Scoping writes to audit_logs would silently drop exactly the rows
    the trail exists to hold.
    """
    from sqlalchemy import update

    from app.models.audit_log import AuditLog

    ws_a, ws_b = two_workspaces
    async with async_session_factory() as db:
        with unscoped():
            row = AuditLog(action="http.post", resource="/api/auth/login",
                           payload={}, workspace_id=None)
            db.add(row)
            await db.commit()
            row_id = row.id

    # Under B's context: audit_logs is exempt, so this must still apply.
    async with async_session_factory() as db:
        token = set_current_workspace(ws_b)
        try:
            await db.execute(
                update(AuditLog).where(AuditLog.id == row_id)
                .values(resource="/api/auth/login?checked")
                .execution_options(synchronize_session=False)
            )
            await db.commit()
        finally:
            reset_current_workspace(token)

    assert (await _read_unscoped(AuditLog, row_id)).resource.endswith("?checked"), (
        "the write filter reached an exempt table"
    )


async def test_no_tenant_context_leaves_writes_alone(two_workspaces):
    """Background workers and migrations run with no tenant bound."""
    from sqlalchemy import update

    ws_a, _ = two_workspaces
    row_id = await _insert_as(ws_a, lambda ws: Agent(
        name="worker probe", agent_type="copilot", workspace_id=ws))

    assert current_workspace.get() is None
    async with async_session_factory() as db:
        await db.execute(
            update(Agent).where(Agent.id == row_id).values(name="touched by a worker")
            .execution_options(synchronize_session=False)
        )
        await db.commit()

    assert (await _read_unscoped(Agent, row_id)).name == "touched by a worker", (
        "a write with no tenant context was filtered"
    )


async def test_unscoped_widens_the_write_path_too(two_workspaces):
    """The escape hatch has to work for writes or callers will bypass it."""
    from sqlalchemy import update

    ws_a, ws_b = two_workspaces
    row_id = await _insert_as(ws_a, lambda ws: Agent(
        name="unscoped write probe", agent_type="copilot", workspace_id=ws))

    async with async_session_factory() as db:
        token = set_current_workspace(ws_b)
        try:
            with unscoped():  # deliberate cross-tenant sweep
                await db.execute(
                    update(Agent).where(Agent.id == row_id).values(name="swept")
                    .execution_options(synchronize_session=False)
                )
                await db.commit()
        finally:
            reset_current_workspace(token)

    assert (await _read_unscoped(Agent, row_id)).name == "swept", (
        "unscoped() did not widen a bulk write"
    )


async def test_orm_unit_of_work_delete_still_works(two_workspaces):
    """`session.delete(obj)` flushes through core, not an ORM DELETE statement.

    Widening the hook to cover `is_delete` must not break the ordinary
    load-then-delete path, which is what most handlers here actually do.
    """
    ws_a, _ = two_workspaces
    row_id = await _insert_as(ws_a, lambda ws: Agent(
        name="uow delete probe", agent_type="copilot", workspace_id=ws))

    async with async_session_factory() as db:
        token = set_current_workspace(ws_a)
        try:
            row = await db.get(Agent, row_id)
            assert row is not None
            await db.delete(row)
            await db.commit()
        finally:
            reset_current_workspace(token)

    assert await _read_unscoped(Agent, row_id) is None, (
        "the ordinary load-then-delete path stopped working"
    )
