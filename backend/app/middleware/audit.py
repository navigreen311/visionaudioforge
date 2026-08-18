"""Audit middleware: logs every request to the audit_logs table (non-blocking).

The README claims an audit trail for compliance; this is the code that has to
actually run for that claim to be true.

Three defects kept the previous version from being safe to enable:

1. ``asyncio.ensure_future`` with no reference held — the event loop only keeps
   a weak reference to a task, so an audit write could be garbage-collected
   before it ran. Tasks are now held in a module-level set until done.
2. No exception handling on the orphaned task — a database that is down turned
   into a bare "Task exception was never retrieved" on stderr and, on Windows,
   a ``RuntimeError: Event loop is closed`` at shutdown. That is the
   "incompatibility" the disable comment was pointing at.
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


async def _write_audit_log(
    user_id: str | None,
    action: str,
    resource: str,
    ip_address: str | None,
    workspace_id: str | None,
) -> None:
    """Persist an audit log entry in a separate DB session (background).

    The column names here are not cosmetic. This previously passed
    ``resource_type`` and ``ip_address`` as constructor arguments; audit_logs
    has ``resource`` and no ip_address column, so every single write raised
    TypeError and was swallowed by the caller's except. The audit trail the
    README advertises had never recorded a row.

    ``workspace_id`` is NOT NULL, so a request that cannot be attributed to a
    workspace is skipped rather than raising on every request — and that skip
    is logged, because an audit trail quietly dropping entries is the failure
    mode this function exists to avoid.
    """
    from app.database import async_session_factory
    from app.models.audit_log import AuditLog

    if not workspace_id:
        logger.debug(
            "Audit entry skipped for %s %s: no workspace on the request",
            action,
            resource,
        )
        return

    async with async_session_factory() as session:
        log = AuditLog(
            user_id=UUID(user_id) if user_id else None,
            action=action,
            resource=resource,
            workspace_id=UUID(workspace_id),
            # ip_address is not a column; keep it in the payload so the record
            # still says where the request came from.
            payload={"ip_address": ip_address} if ip_address else {},
        )
        session.add(log)
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


class AuditMiddleware:
    """Record user_id, HTTP method, path, and client IP for every request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.AUDIT_ENABLED:
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        finally:
            # Read *after* the downstream call: the auth middleware sits inside
            # this one, so the identity is only on the scope by now.
            state = scope.get("state") or {}
            user_id = state.get("user_id")
            workspace_id = state.get("workspace_id")
            client = scope.get("client")

            _spawn(
                _write_audit_log(
                    user_id=str(user_id) if user_id else None,
                    action=scope.get("method", ""),
                    resource=scope.get("path", ""),
                    ip_address=client[0] if client else None,
                    workspace_id=str(workspace_id) if workspace_id else None,
                )
            )
