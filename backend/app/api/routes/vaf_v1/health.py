"""VAF v1 health endpoint — reports service liveness and rough latencies.

This is the ``/api/v1/health`` probe PAF clients call when deciding whether
to use VAF or fall back to browser speech APIs. It is intentionally distinct
from the platform-wide ``/api/health`` (which reports DB/Redis/MinIO).
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque

from fastapi import APIRouter

from app.schemas.vaf_v1.health import VAFHealthResponse, VAFLatencies

router = APIRouter(prefix="/api/v1/health", tags=["VAF v1 / health"])


# ---------------------------------------------------------------------------
# In-process latency tracker — populated by other VAF v1 routes via
# ``record_latency()``. The /health endpoint surfaces a rolling mean. Falls
# back to spec defaults when no samples have been observed yet.
# ---------------------------------------------------------------------------
_DEFAULTS = {"stt": 320.0, "tts": 180.0, "sentiment": 95.0}
_WINDOW = 32
_lock = Lock()
_samples: dict[str, Deque[float]] = {
    "stt": deque(maxlen=_WINDOW),
    "tts": deque(maxlen=_WINDOW),
    "sentiment": deque(maxlen=_WINDOW),
}


def record_latency(component: str, latency_ms: float) -> None:
    """Record a latency observation for a VAF component."""
    if component not in _samples:
        return
    with _lock:
        _samples[component].append(float(latency_ms))


def _mean_or_default(component: str) -> float:
    with _lock:
        bucket = _samples[component]
        if not bucket:
            return _DEFAULTS[component]
        return round(sum(bucket) / len(bucket), 2)


@router.get("", response_model=VAFHealthResponse)
async def get_vaf_health() -> VAFHealthResponse:
    """Report VAF service liveness and recent component latencies."""
    return VAFHealthResponse(
        status="ok",
        latencies=VAFLatencies(
            stt=_mean_or_default("stt"),
            tts=_mean_or_default("tts"),
            sentiment=_mean_or_default("sentiment"),
        ),
        version="mock-1.0.0",
    )
