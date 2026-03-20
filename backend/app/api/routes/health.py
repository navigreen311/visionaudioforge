"""Health check endpoint with real service probes."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import async_session_factory
from app.schemas.common import HealthResponse, ServiceHealth

router = APIRouter(tags=["health"])

_start_time = time.monotonic()


async def _check_database() -> ServiceHealth:
    """Probe PostgreSQL with SELECT 1."""
    try:
        t0 = time.monotonic()
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.monotonic() - t0) * 1000
        return ServiceHealth(status="up", latency_ms=round(latency, 2))
    except Exception:
        return ServiceHealth(status="down", latency_ms=None)


async def _check_redis() -> ServiceHealth:
    """Probe Redis with PING."""
    try:
        import redis.asyncio as aioredis

        t0 = time.monotonic()
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        latency = (time.monotonic() - t0) * 1000
        return ServiceHealth(status="up", latency_ms=round(latency, 2))
    except Exception:
        return ServiceHealth(status="down", latency_ms=None)


async def _check_minio() -> ServiceHealth:
    """Best-effort MinIO probe (sync client, so status may be 'unknown')."""
    try:
        from minio import Minio

        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
        client.list_buckets()
        return ServiceHealth(status="up", latency_ms=None)
    except Exception:
        return ServiceHealth(status="unknown", latency_ms=None)


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    db = await _check_database()
    redis = await _check_redis()
    minio = await _check_minio()

    # Determine overall status
    if db.status == "down":
        overall = "unhealthy"
    elif redis.status == "down" or minio.status == "down":
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthResponse(
        status=overall,
        version="1.0.0",
        services={
            "database": db,
            "redis": redis,
            "minio": minio,
        },
        uptime_seconds=round(time.monotonic() - _start_time, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
