"""Middleware that assigns a unique request ID to every request.

Raw ASGI rather than ``BaseHTTPMiddleware``: the contextvar set here has to be
visible to the route handler *and* to the global exception handler, which lives
outside the user middleware stack. ``BaseHTTPMiddleware`` runs the downstream
app in a child task, so a contextvar set in ``dispatch`` does not reliably
survive back out to ``ServerErrorMiddleware``. Stamping the ASGI ``scope``
does, because the scope dict is shared by every layer.
"""

import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging_config import request_id_ctx

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = _header(scope, REQUEST_ID_HEADER) or str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = rid
        token = request_id_ctx.set(rid)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = rid
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_ctx.reset(token)


def _header(scope: Scope, name: str) -> str | None:
    """Read a single request header from the raw ASGI scope."""
    wanted = name.lower().encode("latin-1")
    for key, value in scope.get("headers") or ():
        if key.lower() == wanted:
            return value.decode("latin-1")
    return None
