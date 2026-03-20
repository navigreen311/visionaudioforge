from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.ws.capture import CaptureWebSocket

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="VisionAudioForge — AI-powered vision & audio analysis platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.websocket("/ws/live/stream/{session_id}")
async def websocket_capture_stream(websocket: WebSocket, session_id: str):
    handler = CaptureWebSocket()
    await handler.handle_connection(websocket, session_id)
