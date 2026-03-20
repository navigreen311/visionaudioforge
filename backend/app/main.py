from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="VisionAudioForge — AI-powered vision & audio analysis platform",
)

# Middleware is applied in reverse order — TimingMiddleware wraps outermost.
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
