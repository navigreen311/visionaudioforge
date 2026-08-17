"""App-level authentication — the trust boundary for every route at once.

Why middleware and not ``Depends(get_current_user)`` on each router:

* There are 60+ route modules. A per-route dependency is unreviewable (you have
  to read every file to know the answer) and it fails *open* — the module
  someone adds next month is public until a human notices.
* Middleware fails *closed*. A new route is protected the moment it is
  registered; making it public requires editing
  :mod:`app.core.auth_policy`, which is a one-line, obvious diff.

Implemented as raw ASGI rather than ``BaseHTTPMiddleware`` so that it also
covers ``websocket`` scopes (``BaseHTTPMiddleware`` silently passes those
through) and so that it adds no task-group hop to the hot path.
"""

from __future__ import annotations

from typing import Any, MutableMapping

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.core.auth_policy import is_public
from app.core.identity import AuthError, Identity, resolve_identity
from app.core.logging_config import user_id_ctx, workspace_id_ctx

# Sent on an unauthenticated WebSocket handshake. 1008 = policy violation.
WS_POLICY_VIOLATION = 1008


def attach_identity(scope: MutableMapping[str, Any], identity: Identity | None) -> None:
    """Publish *identity* on the ASGI scope so ``request.state`` can see it."""
    state = scope.setdefault("state", {})
    state["identity"] = identity
    state["user_id"] = identity.user_id if identity else None
    state["workspace_id"] = identity.workspace_id if identity else None
    state["auth_method"] = identity.auth_method if identity else None


class AuthenticationMiddleware:
    """Reject any request that does not carry a verifiable identity.

    Args:
        app: the downstream ASGI application.
        required: overrides ``settings.AUTH_REQUIRED`` when not ``None``.
            Present so a test can build a deliberately-open app without
            mutating global settings.
    """

    def __init__(self, app: ASGIApp, required: bool | None = None) -> None:
        self.app = app
        self._required_override = required

    @property
    def required(self) -> bool:
        if self._required_override is not None:
            return self._required_override
        return bool(settings.AUTH_REQUIRED)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        path = scope.get("path", "")
        method = scope.get("method", "GET" if scope["type"] == "http" else "WEBSOCKET")

        if scope["type"] == "http" and is_public(path, method):
            attach_identity(scope, None)
            await self.app(scope, receive, send)
            return

        try:
            identity: Identity | None = await resolve_identity(headers)
        except AuthError as exc:
            if not self.required:
                # Opted out: an unusable credential is not fatal, but we still
                # refuse to invent an identity for it.
                attach_identity(scope, None)
                await self.app(scope, receive, send)
                return
            await self._deny(scope, receive, send, exc)
            return

        attach_identity(scope, identity)
        tokens = (
            user_id_ctx.set(str(identity.user_id)),
            workspace_id_ctx.set(
                str(identity.workspace_id) if identity.workspace_id else ""
            ),
        )
        try:
            await self.app(scope, receive, send)
        finally:
            user_id_ctx.reset(tokens[0])
            workspace_id_ctx.reset(tokens[1])

    async def _deny(
        self, scope: Scope, receive: Receive, send: Send, exc: AuthError
    ) -> None:
        attach_identity(scope, None)

        if scope["type"] == "websocket":
            # Drain the handshake before closing; ASGI servers expect the app
            # to consume ``websocket.connect`` first.
            message: Message = await receive()
            if message["type"] == "websocket.connect":
                await send(
                    {
                        "type": "websocket.close",
                        "code": WS_POLICY_VIOLATION,
                        "reason": exc.detail,
                    }
                )
            return

        response = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)
