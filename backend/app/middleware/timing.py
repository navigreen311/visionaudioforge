"""Middleware that measures request duration and logs it.

Raw ASGI so the ``X-Process-Time`` header can be injected into the response
start message directly. ``BaseHTTPMiddleware`` buffers the response through an
extra task, which both inflates the number it is trying to measure and drops
the header when a downstream layer streams.
"""

import time

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging_config import get_logger

logger = get_logger("timing")

PROCESS_TIME_HEADER = "X-Process-Time"


class TimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        status_code = 500

        async def send_with_timing(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration_ms = round((time.monotonic() - start) * 1000, 2)
                headers = MutableHeaders(scope=message)
                headers[PROCESS_TIME_HEADER] = str(duration_ms)
            await send(message)

        try:
            await self.app(scope, receive, send_with_timing)
        finally:
            logger.info(
                "request completed",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status_code": status_code,
                    "duration_ms": round((time.monotonic() - start) * 1000, 2),
                },
            )
