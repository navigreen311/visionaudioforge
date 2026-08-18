"""Refuse requests that name a workspace other than the caller's own.

The authentication middleware establishes *who* the caller is and which tenant
their token was minted for. It does not stop them asking for someone else's
tenant, and the routes do not either: almost every endpoint here takes
``workspace_id`` as a query parameter or a body field, and uses it verbatim.

The effect, before this middleware existed, was that a token for workspace A
could read and write workspace B's rows simply by saying so::

    GET  /api/datasets?workspace_id=<B>          -> 200, B's datasets
    GET  /api/datasets/<B's dataset id>          -> 200, B's dataset
    POST /api/registry/register {workspace_id:B} -> 201, a row inside B

Fixing that route by route means editing 60+ modules and trusting that the next
one remembers. This does it in one place, on the same principle as the auth
middleware: the boundary fails closed, and an exception is an obvious one-line
diff in :mod:`app.core.auth_policy`.

The rule is narrow and therefore safe: a request may omit ``workspace_id``, and
it may pass its *own*. Naming a different one is 403. That leaves route-level
scoping (what a request with no workspace should see) to the routes, which is
where it belongs — see ``docs/auth.md``.

Raw ASGI, like the auth middleware, because it has to buffer and replay the
request body: reading the body in a ``BaseHTTPMiddleware`` consumes the stream
the route handler is about to read.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.auth_policy import is_public

# A body larger than this is not inspected. Uploads are multipart and carry no
# JSON workspace field, and buffering an arbitrarily large body to look for one
# would be a denial-of-service lever.
MAX_INSPECTED_BODY = 1 * 1024 * 1024

WORKSPACE_FIELD = "workspace_id"


def _query_workspaces(scope: Scope) -> list[str]:
    raw = scope.get("query_string") or b""
    if not raw:
        return []
    return [v for v in parse_qs(raw.decode("latin-1")).get(WORKSPACE_FIELD, []) if v]


def _body_workspaces(body: bytes, content_type: str) -> list[str]:
    """Top-level ``workspace_id`` values in a JSON body.

    Only the top level: a nested one is data the route is storing, not a tenant
    selector, and rejecting those would break legitimate payloads.
    """
    if not body or "json" not in content_type:
        return []
    try:
        parsed = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return []

    candidates: list[object] = []
    if isinstance(parsed, dict):
        candidates.append(parsed.get(WORKSPACE_FIELD))
    elif isinstance(parsed, list):
        candidates.extend(
            item.get(WORKSPACE_FIELD) for item in parsed if isinstance(item, dict)
        )
    return [str(value) for value in candidates if value not in (None, "")]


class TenantGuardMiddleware:
    """403 any request that names a workspace the token was not minted for."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")
        if is_public(path, method):
            await self.app(scope, receive, send)
            return

        own = (scope.get("state") or {}).get("workspace_id")
        if not own:
            # No authenticated tenant to compare against: either the suite has
            # opted out of the auth boundary, or the token carries no workspace.
            # Either way this middleware has no opinion.
            await self.app(scope, receive, send)
            return

        own_str = str(own)

        for requested in _query_workspaces(scope):
            if requested != own_str:
                await self._deny(scope, receive, send, requested, "query")
                return

        # Only buffer a body when there could be one.
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            body, replay = await self._buffer_body(receive)
            content_type = ""
            for name, value in scope.get("headers") or []:
                if name == b"content-type":
                    content_type = value.decode("latin-1").lower()
                    break

            for requested in _body_workspaces(body, content_type):
                if requested != own_str:
                    await self._deny(scope, replay, send, requested, "body")
                    return

            await self.app(scope, replay, send)
            return

        await self.app(scope, receive, send)

    async def _buffer_body(self, receive: Receive) -> tuple[bytes, Receive]:
        """Read the body, then hand back a receive that replays it verbatim."""
        chunks: list[bytes] = []
        total = 0
        truncated = False

        while True:
            message = await receive()
            if message["type"] != "http.request":
                # A disconnect mid-body: replay what we have and let the app see it.
                chunks.append(b"")
                break
            chunk = message.get("body", b"")
            total += len(chunk)
            if total <= MAX_INSPECTED_BODY:
                chunks.append(chunk)
            else:
                truncated = True
                chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        # An oversized body is replayed but not trusted for inspection.
        return (b"" if truncated else body), replay

    async def _deny(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        requested: str,
        source: str,
    ) -> None:
        response = JSONResponse(
            status_code=403,
            content={
                "detail": (
                    "This request names a workspace outside the session. The "
                    "workspace is taken from your token; remove the "
                    f"{WORKSPACE_FIELD} you sent, or sign in to that workspace."
                ),
                "requested_workspace": requested,
                "source": source,
            },
        )
        await response(scope, receive, send)
