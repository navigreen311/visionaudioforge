import os
import traceback

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import settings
from app.middleware.audit import AuditMiddleware
from app.middleware.compression import GZIP_MINIMUM_SIZE, GZipMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware
from app.ws.capture import CaptureWebSocket
from app.ws.copilot import copilot_ws_handler
from app.ws.manager import manager  # noqa: F401 — re-export for convenience

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="VisionAudioForge — Elite Multimodal AI Platform (28 modules, 100+ endpoints)",
)

# ---------------------------------------------------------------------------
# Middleware (order matters — outermost first)
# ---------------------------------------------------------------------------
_cors_origins_raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# NOTE: Custom middlewares disabled for local dev — compatibility issue
# with uvicorn 0.42 + starlette 0.52 on Windows.
# app.add_middleware(RequestIDMiddleware)
# app.add_middleware(TimingMiddleware)
# app.add_middleware(AuditMiddleware)
# app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_SIZE)

# ---------------------------------------------------------------------------
# Global exception handler (surface 500 errors during development)
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    print("".join(tb))
    return JSONResponse(status_code=500, content={"detail": str(exc)})

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
