"""Audit middleware: logs every request to the audit_logs table (non-blocking).

The README claims an audit trail for compliance; this is the code that has to
actually run for that claim to be true.

It has never written a row. The middleware was enabled and the write path was
exercised on every single request, but ``AuditLog`` was constructed with field
names the model does not have::

    TypeError: 'resource_type' is an invalid keyword argument for AuditLog

The model's columns are ``user_id, action, resource, payload, timestamp,
workspace_id``. The middleware passed ``resource_type`` and ``ip_address``.
Correcting those two names is still not enough: ``workspace_id`` is
``nullable=False`` and was never supplied, so every insert would then have
failed on a NOT NULL violation instead. Because the write is fire-and-forget
the failure only ever surfaced as a WARNING in the log, which is why an audit
trail that recorded nothing looked healthy.

Unauthenticated requests are recorded with a NULL workspace as of migration
017. Before it, ``workspace_id`` was NOT NULL and every rejected request —
every failed login — had to be dropped.

Earlier defects, fixed when the middleware was re-enabled:

1. ``asyncio.ensure_future`` with no reference held — the event loop only keeps
   a weak reference to a task, so an audit write could be garbage-collected
   before it ran. Tasks are now held in a module-level set until done.
2. No exception handling on the orphaned task — a database that is down turned
   into a bare "Task exception was never retrieved" on stderr and, on Windows,
   a ``RuntimeError: Event loop is closed`` at shutdown.
3. It re-decoded the JWT itself. The auth middleware has already done that, so
   the identity is read off the ASGI scope instead.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger("audit")

# Strong references to in-flight writes. Without this the loop may collect a
# task mid-await and the audit entry silently disappears.
_pending: set[asyncio.Task[None]] = set()

# audit_logs.resource is String(200). A path longer than that would fail the
# insert, which — being fire-and-forget — would again be invisible.
RESOURCE_MAX_LEN = 200

# Liveness and scrape endpoints are deliberately not audited. Container
# healthchecks hit /api/health every 10 seconds and Prometheus scrapes
# /api/metrics on its own schedule; recording them adds thousands of rows a day
# that carry no security meaning and bury the events that do. Everything else
# on the public allowlist IS audited — a failed login is the single most
# important row this table holds.
AUDIT_EXEMPT_PATHS = frozenset({"/api/health", "/api/metrics"})


async def _write_audit_log(
    *,
    user_id: str | None,
    workspace_id: str | None,
    action: str,
    resource: str,
    payload: dict[str, Any],
) -> None:
    """Persist an audit log entry in a separate DB session (background)."""
    from app.database import async_session_factory
    from app.models.audit_log import AuditLog

    async with async_session_factory() as session:
        session.add(
            AuditLog(
                user_id=UUID(user_id) if user_id else None,
                workspace_id=UUID(workspace_id) if workspace_id else None,
                action=action,
                resource=resource[:RESOURCE_MAX_LEN],
                payload=payload,
            )
        )
        await session.commit()


def _spawn(coro: Any) -> None:
    """Run *coro* detached, keeping a reference and swallowing failures."""
    try:
        task = asyncio.ensure_future(coro)
    except RuntimeError:  # no running loop (e.g. interpreter shutting down)
        coro.close()
        return

    _pending.add(task)

    def _done(finished: asyncio.Task[None]) -> None:
        _pending.discard(finished)
        if finished.cancelled():
            return
        exc = finished.exception()
        if exc is not None:
            logger.warning("audit log write failed", exc_info=exc)

    task.add_done_callback(_done)


def _client_ip(scope: Scope) -> str | None:
    """Prefer the proxy's X-Forwarded-For over the socket peer.

    Behind nginx every request appears to come from the proxy, so the socket
    address is the same for all of them and worthless in an audit trail.
    """
    for key, value in scope.get("headers") or ():
        if key.lower() == b"x-forwarded-for":
            forwarded = value.decode("latin-1").split(",")[0].strip()
            if forwarded:
                return forwarded
    client = scope.get("client")
    return client[0] if client else None


class AuditMiddleware:
    """Record who did what, to which resource, in which workspace."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.AUDIT_ENABLED:
            await self.app(scope, receive, send)
            return

        status_code: int | None = None

        async def send_capturing_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_capturing_status)
        finally:
            self._record(scope, status_code)

    def _record(self, scope: Scope, status_code: int | None) -> None:
        # Read *after* the downstream call: the auth middleware sits inside this
        # one, so the identity is only on the scope by now.
        state = scope.get("state") or {}
        workspace_id = state.get("workspace_id")

        method = scope.get("method", "")
        path = scope.get("path", "")

        if path in AUDIT_EXEMPT_PATHS:
            return

        # Unauthenticated requests are recorded too, with a NULL workspace.
        # This is the case that matters most: a failed login is the first thing
        # anyone asks an audit trail for, and it is precisely the event that has
        # no tenant yet. audit_logs.workspace_id was NOT NULL until revision
        # 017, which is why these were previously dropped.
        user_id = state.get("user_id")

        _spawn(
            _write_audit_log(
                user_id=str(user_id) if user_id else None,
                workspace_id=str(workspace_id) if workspace_id else None,
                # Dotted verbs match the convention used by the service layer
                # ("custody.create"), so audit rows from both sources sort and
                # filter together.
                action=f"http.{method.lower()}" if method else "http.request",
                resource=path,
                payload={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "ip": _client_ip(scope),
                    "request_id": state.get("request_id"),
                    "auth_method": state.get("auth_method"),
                },
            )
        )
