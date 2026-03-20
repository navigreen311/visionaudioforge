from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.ws.copilot import copilot_ws_handler

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


@app.websocket("/ws/agents/stream")
async def ws_copilot_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming copilot chat."""
    await copilot_ws_handler(websocket)
