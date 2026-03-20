from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.middleware.audit import AuditMiddleware

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
app.add_middleware(AuditMiddleware)

app.include_router(api_router)
