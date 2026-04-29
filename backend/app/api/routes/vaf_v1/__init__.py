"""VAF v1 mock API surface — PAF integration endpoints.

This package owns ``/api/v1/*`` routes. Sub-routers are aggregated into
``vaf_v1_router`` which is mounted from :mod:`app.api.router`.

WS10 (this PR) owns: stt, tts, speaker, audio, health.
WS11 (sibling) owns: sentiment, meeting, vision, translate (mounted on
the same aggregator).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.vaf_v1 import audio, health, speaker, stt, tts

vaf_v1_router = APIRouter()

# WS10 sub-routers
vaf_v1_router.include_router(health.router)
vaf_v1_router.include_router(stt.router)
vaf_v1_router.include_router(tts.router)
vaf_v1_router.include_router(speaker.router)
vaf_v1_router.include_router(audio.router)

# WS11 sub-routers (sentiment, meeting, vision, translate) are mounted by
# WS11's PR via ``vaf_v1_router.include_router(...)`` calls added below.

__all__ = ["vaf_v1_router"]
