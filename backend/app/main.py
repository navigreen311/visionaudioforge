import os
import traceback
import uuid

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import settings
from app.core.logging_config import get_logger, request_id_ctx
from app.middleware.audit import AuditMiddleware
from app.middleware.auth import AuthenticationMiddleware
from app.middleware.compression import GZIP_MINIMUM_SIZE, GZipMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware
from app.ws.capture import CaptureWebSocket
from app.ws.copilot import copilot_ws_handler
from app.ws.manager import manager  # noqa: F401 — re-export for convenience

logger = get_logger("app")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="VisionAudioForge — Elite Multimodal AI Platform (28 modules, 100+ endpoints)",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
# Starlette's `add_middleware` *prepends*, so the LAST call below is the
# OUTERMOST layer. Reading bottom-up gives the request order:
#
#   CORS -> RequestID -> Timing -> GZip -> Audit -> Auth -> routes
#
# Rationale for that order:
#   * CORS outermost so preflights are answered and so error responses (401,
#     500) still carry the headers a browser needs to read them.
#   * RequestID next so every response — including denials — is traceable.
#   * Timing outside GZip, to measure compression as part of the response.
#   * Auth innermost, so an unauthenticated request is still timed, logged and
#     stamped with a request ID.
#
# All four custom middlewares were previously commented out as "incompatible
# with uvicorn 0.42 + starlette 0.52 on Windows". The version pin was a red
# herring; see docs/auth.md ("Middleware restoration") for the actual defect
# and fix.
_cors_origins_raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]

app.add_middleware(AuthenticationMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_SIZE)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return an opaque 500 and keep the diagnosis server-side.

    The previous implementation returned ``str(exc)`` to the caller, which
    hands an anonymous client the shape of the failure — SQL fragments,
    absolute file paths, key names. The traceback now goes to the log, and the
    caller gets a request ID to quote in a support ticket instead.
    """
    request_id = (
        getattr(request.state, "request_id", None)
        or request_id_ctx.get("")
        or str(uuid.uuid4())
    )

    logger.error(
        "unhandled exception",
        exc_info=exc,
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "request_id": request_id,
        },
    )

    content: dict[str, object] = {
        "detail": "Internal server error",
        "request_id": request_id,
    }
    if settings.DEBUG_ERRORS:
        content["exception"] = f"{type(exc).__name__}: {exc}"
        content["traceback"] = traceback.format_exception(
            type(exc), exc, exc.__traceback__
        )

    return JSONResponse(
        status_code=500,
        content=content,
        headers={"X-Request-ID": request_id},
    )


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------
app.include_router(api_router)

# ---------------------------------------------------------------------------
# WebSocket routes
# ---------------------------------------------------------------------------
_capture = CaptureWebSocket()


@app.websocket("/ws/live/stream/{session_id}")
async def ws_live_stream(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for live video capture streaming."""
    await _capture.handle_connection(websocket, session_id)


@app.websocket("/ws/agents/stream")
async def ws_copilot_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming copilot chat."""
    await copilot_ws_handler(websocket)
