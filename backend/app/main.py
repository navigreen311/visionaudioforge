from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.middleware.audit import AuditMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware
from app.ws.capture import CaptureWebSocket
from app.ws.copilot import copilot_ws_handler
from app.ws.manager import manager  # noqa: F401 — re-export for convenience

app = FastAPI(
    title=settings.APP_NAME,
    version="0.2.0",
    description="VisionAudioForge — AI-powered vision & audio analysis platform",
)

# ---------------------------------------------------------------------------
# Middleware (order matters — outermost first)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(AuditMiddleware)

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
