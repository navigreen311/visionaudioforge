"""VAF v1 mock API surface — PAF integration endpoints.

This package owns ``/api/v1/*`` routes. Sub-routers are aggregated into
``vaf_v1_router`` which is mounted from :mod:`app.api.router`.

WS10 (this PR) owns: stt, tts, speaker, audio, health.
WS11 (sibling) owns: sentiment, meeting, vision, translate (mounted on
the same aggregator).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.vaf_v1 import audio, health, meeting, sentiment, speaker, stt, translate, tts, vision

vaf_v1_router = APIRouter()

# WS10 sub-routers
vaf_v1_router.include_router(health.router)
vaf_v1_router.include_router(stt.router)
vaf_v1_router.include_router(tts.router)
vaf_v1_router.include_router(speaker.router)
vaf_v1_router.include_router(audio.router)

# WS11 sub-routers
vaf_v1_router.include_router(sentiment.router)
vaf_v1_router.include_router(meeting.router)
vaf_v1_router.include_router(vision.router)
vaf_v1_router.include_router(translate.router)

__all__ = ["vaf_v1_router"]
