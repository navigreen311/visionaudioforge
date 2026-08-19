"""Workspace scoping enforced at the session, not at each route.

The problem this solves
-----------------------

``TenantGuardMiddleware`` refuses a request that *names* a workspace other than
the caller's. It cannot help a route whose id arrives in the path, because a path
parameter names no workspace - the row itself has to be checked. Doing that route
by route meant 185 of the 191 by-id routes had no check at all, and every route
added later would start life the same way. Alerts, agent memories, annotations,
investigation cases, incident timelines, evidence bundles and chain-of-custody
exports were all readable across tenants with nothing but an id.

The fix
-------

A SQLAlchemy ``do_orm_execute`` hook adds ``WHERE workspace_id = :current`` to
every ORM SELECT touching a model that has a ``workspace_id`` column, driven by a
context variable the authentication middleware sets. A route that forgets to
filter now gets an empty result instead of another tenant's row, and a route
added tomorrow is scoped the moment it queries.

This is the same shape as the auth middleware: enforce once, at the boundary, and
make the exceptions explicit and few.

What it does *not* do
---------------------

* It applies to ORM SELECTs. Bulk ``update()``/``delete()`` statements and raw
  SQL are untouched - a handler that mutates by id without loading the row first
  is still its own responsibility. Most here load first, which is why this
  covers the exposure.
* It is not a substitute for Postgres row-level security. It is enforced in this
  process, so anything reaching the database another way is unaffected.

Exemptions
----------

``EXEMPT_TABLES`` names the models that must stay visible across workspaces:

* ``users`` - login resolves an account by email before any workspace exists,
  and membership checks read users from the workspace being inspected.
* ``workspaces`` - a workspace row is the tenant; scoping it to itself would
  make it unreadable. ``workspaces.py`` guards these with its own membership
  check.
* ``audit_logs`` - the audit middleware writes entries for requests that have no
  workspace yet (registration, login), and an audit trail that can be filtered
  by the thing it audits is not much of an audit trail. Reads are guarded by the
  route.

Use :func:`unscoped` for a deliberate cross-tenant query, and say why in a
comment. It is a context manager rather than a flag so the widening cannot leak
past the block that asked for it.
"""

from __future__ import annotations

import contextlib
import logging
from contextvars import ContextVar, Token
from typing import Iterator
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

logger = logging.getLogger(__name__)

# The workspace every ORM read is confined to. Unset means "no tenant context" -
# the filter stays out of the way, which is what login, registration and the
# background workers need.
current_workspace: ContextVar[UUID | None] = ContextVar("current_workspace", default=None)

# Set inside `unscoped()`. Separate from the value above so leaving the block
# restores the original scope rather than clearing it.
_bypass: ContextVar[bool] = ContextVar("workspace_filter_bypass", default=False)

EXEMPT_TABLES: frozenset[str] = frozenset({"users", "workspaces", "audit_logs"})


def set_current_workspace(workspace_id: UUID | str | None) -> Token:
    """Bind the tenant for this task. Returns a token for :func:`reset`."""
    if workspace_id is None:
        return current_workspace.set(None)
    if not isinstance(workspace_id, UUID):
        try:
            workspace_id = UUID(str(workspace_id))
        except (ValueError, AttributeError, TypeError):
            # A malformed claim must not silently widen the scope.
            logger.warning("ignoring unparseable workspace id in tenant context")
            return current_workspace.set(None)
    return current_workspace.set(workspace_id)


def reset_current_workspace(token: Token) -> None:
    current_workspace.reset(token)


@contextlib.contextmanager
def unscoped() -> Iterator[None]:
    """Run a deliberate cross-workspace query.

    For code that legitimately spans tenants - platform administration, a
    migration, a background sweep. Always leave a comment saying which, because
    the next reader's default assumption should be that a query is scoped.
    """
    token = _bypass.set(True)
    try:
        yield
    finally:
        _bypass.reset(token)


def _parent_scope(mapper) -> tuple | None:
    """Find a foreign key from *mapper* to a table that is workspace-scoped.

    Child tables - agent memories, pipeline runs, experiment epochs, evidence
    bundle items, annotations - mostly carry no ``workspace_id`` of their own.
    They belong to a tenant through their parent, and scoping them by that
    relationship avoids 23 migrations and a backfill to say something the schema
    already knows.

    Returns ``(local_column, parent_table, parent_id_column)`` or ``None`` when
    the class has no scoped parent - which is the correct answer for rows that
    hang off a *user* (sessions, two-factor secrets, appearance preferences) or
    are genuinely global (model cost rates).
    """
    from sqlalchemy import inspect as sa_inspect  # local: avoids an import cycle

    table = mapper.local_table
    if table is None:
        return None

    for column in table.columns:
        for fk in column.foreign_keys:
            parent_table = fk.column.table
            if parent_table.name in EXEMPT_TABLES:
                continue
            if "workspace_id" in parent_table.columns:
                return (column, parent_table, fk.column)

    del sa_inspect
    return None


# Built once per class: the shape of a table does not change at runtime, and
# walking foreign keys on every query would be wasteful.
_parent_scope_cache: dict[type, tuple | None] = {}


def _scoped_entities(execute_state) -> list[tuple]:
    """(class, criteria_builder) for every scopable mapped class in this query.

    Two ways a class can be scoped: its own ``workspace_id`` column, or a foreign
    key to a parent that has one.
    """
    from sqlalchemy import select  # local: keeps module import cheap

    entities: list[tuple] = []
    for mapper in execute_state.all_mappers:
        table_name = getattr(mapper.local_table, "name", None)
        if table_name in EXEMPT_TABLES:
            continue

        cls = mapper.class_
        if "workspace_id" in mapper.columns:
            entities.append((cls, "own"))
            continue

        if cls not in _parent_scope_cache:
            _parent_scope_cache[cls] = _parent_scope(mapper)
        parent = _parent_scope_cache[cls]
        if parent is not None:
            entities.append((cls, parent))

    del select
    return entities


def install_workspace_filter(session_class: type[Session] | type = Session) -> None:
    """Register the scoping hook on *session_class*.

    Idempotent: registering twice would apply the criteria twice, which is
    harmless but confusing in a query log, so guard with SQLAlchemy's own check.
    """
    if event.contains(session_class, "do_orm_execute", _apply_workspace_filter):
        return
    event.listen(session_class, "do_orm_execute", _apply_workspace_filter)


def _apply_workspace_filter(execute_state) -> None:
    if not execute_state.is_select:
        return
    # A relationship load inherits the criteria already applied to its parent;
    # re-applying would filter the *related* table by the parent's column.
    if execute_state.is_relationship_load:
        return
    if _bypass.get():
        return

    workspace_id = current_workspace.get()
    if workspace_id is None:
        return

    from sqlalchemy import select

    for entity, how in _scoped_entities(execute_state):
        if how == "own":
            criteria = entity.workspace_id == workspace_id
        else:
            local_column, parent_table, parent_id = how
            # The child belongs to the tenant that owns its parent. A correlated
            # IN rather than a join, so it composes with whatever the caller's
            # own query is already doing.
            criteria = local_column.in_(
                select(parent_id).where(parent_table.c.workspace_id == workspace_id)
            )

        execute_state.statement = execute_state.statement.options(
            # A plain expression, not a lambda. `with_loader_criteria` caches
            # lambda criteria and tracks their closure variables; getting that
            # wrong would bake one request's workspace into every later query,
            # which is the exact bug this module exists to prevent. An expression
            # is rebuilt per statement and cannot be cached across tenants.
            with_loader_criteria(entity, criteria, include_aliases=True)
        )
