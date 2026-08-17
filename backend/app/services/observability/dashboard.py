"""SRE Dashboard data service.

Provides system-overview, pipeline-health, inference, error-taxonomy and
queue metrics for the observability dashboard.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.observability import metrics_source

logger = logging.getLogger(__name__)

#: Returned wherever a figure has no recorded source. The dashboard renders
#: these as "unknown"; they must never be replaced with a plausible number.
UNMEASURED: None = None

# ---------------------------------------------------------------------------
# Service start time — used for uptime calculation
# ---------------------------------------------------------------------------
_SERVICE_START = time.time()


class SREDashboardService:
    """Aggregate metrics for the SRE dashboard."""

    # ------------------------------------------------------------------
    # System overview
    # ------------------------------------------------------------------

    @staticmethod
    async def get_system_overview(db: AsyncSession) -> dict[str, Any]:
        """Return top-level health/performance summary.

        Returns
        -------
        dict with keys: api_status, db_status, redis_status, uptime_s,
        total_requests_24h, error_rate_24h, avg_latency_ms, p99_latency_ms
        """
        # DB connectivity check
        db_status = "healthy"
        try:
            await db.execute(text("SELECT 1"))
        except Exception:
            db_status = "unhealthy"

        # Redis check (best-effort)
        redis_status = "unknown"
        try:
            import redis as _redis

            r = _redis.Redis()
            r.ping()
            redis_status = "healthy"
        except Exception:
            redis_status = "unavailable"

        uptime_s = round(time.time() - _SERVICE_START, 2)

        # Measured from the in-process Prometheus counters. These cover the
        # lifetime of this process, not a rolling 24h window — `metrics_window`
        # says so rather than letting the *_24h key names overstate it.
        total_requests, error_count = metrics_source.request_totals()
        latency = metrics_source.average_request_latency_ms()

        error_rate = (
            round(error_count / total_requests, 6) if total_requests else UNMEASURED
        )
        avg_latency_ms = round(latency.value, 2) if latency.observed else UNMEASURED

        return {
            "api_status": "healthy",
            "db_status": db_status,
            "redis_status": redis_status,
            "uptime_s": uptime_s,
            "metrics_window": "process_lifetime",
            "total_requests_24h": total_requests,
            "error_count": error_count,
            "error_rate_24h": error_rate,
            "avg_latency_ms": avg_latency_ms,
            # The duration histogram has no quantile buckets configured, so a
            # p99 cannot be derived from it.
            "p99_latency_ms": UNMEASURED,
            "unmeasured": [
                name
                for name, value in (
                    ("error_rate_24h", error_rate),
                    ("avg_latency_ms", avg_latency_ms),
                    ("p99_latency_ms", UNMEASURED),
                )
                if value is None
            ],
        }

    # ------------------------------------------------------------------
    # Pipeline health
    # ------------------------------------------------------------------

    @staticmethod
    async def get_pipeline_health(db: AsyncSession) -> dict[str, Any]:
        """Return pipeline execution metrics."""
        # Try querying actual pipeline tables; fall back to stubs
        try:
            from app.models.pipeline import PipelineRun  # type: ignore[attr-defined]

            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            total = (
                await db.execute(
                    select(func.count()).select_from(PipelineRun).where(
                        PipelineRun.created_at >= cutoff
                    )
                )
            ).scalar() or 0
            success = (
                await db.execute(
                    select(func.count())
                    .select_from(PipelineRun)
                    .where(
                        PipelineRun.created_at >= cutoff,
                        PipelineRun.status == "success",
                    )
                )
            ).scalar() or 0
            success_rate = round(success / max(total, 1), 4)
            active = (
                await db.execute(
                    select(func.count())
                    .select_from(PipelineRun)
                    .where(PipelineRun.status == "running")
                )
            ).scalar() or 0
        except Exception:
            # No pipeline table to read — report unknown rather than inventing
            # a run count and a healthy-looking success rate.
            logger.warning("Pipeline health unavailable: could not query PipelineRun")
            total = UNMEASURED
            success = UNMEASURED
            success_rate = UNMEASURED
            active = UNMEASURED

        duration = metrics_source.histogram_average(
            "pipeline_run_duration_seconds", scale=1000.0
        )
        avg_duration_ms = round(duration.value, 2) if duration.observed else UNMEASURED
        failed_runs: list[dict[str, Any]] = []

        return {
            "active_pipelines": active,
            "runs_24h": total,
            "successful_runs_24h": success,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration_ms,
            "failed_runs": failed_runs,
            "unmeasured": [
                name
                for name, value in (
                    ("active_pipelines", active),
                    ("runs_24h", total),
                    ("success_rate", success_rate),
                    ("avg_duration_ms", avg_duration_ms),
                )
                if value is None
            ],
        }

    # ------------------------------------------------------------------
    # Inference metrics
    # ------------------------------------------------------------------

    @staticmethod
    async def get_inference_metrics() -> dict[str, Any]:
        """Return ML inference metrics, as far as they are actually recorded."""
        inference = metrics_source.histogram_average(
            "model_inference_duration_seconds", scale=1000.0
        )
        queue = metrics_source.gauge_value("inference_queue_depth")

        avg_inference_ms = (
            round(inference.value, 2) if inference.observed else UNMEASURED
        )
        # sample_count is the number of inferences the histogram has observed —
        # a real count, not an estimate.
        inference_count = inference.sample_count if inference.observed else UNMEASURED
        queue_depth = int(queue.value) if queue.observed else UNMEASURED

        return {
            # No model registry counter exists, and no GPU monitoring is wired.
            "models_loaded": UNMEASURED,
            "inference_count_24h": inference_count,
            "avg_inference_ms": avg_inference_ms,
            "gpu_utilization_pct": UNMEASURED,
            "queue_depth": queue_depth,
            "metrics_window": "process_lifetime",
            "unmeasured": [
                name
                for name, value in (
                    ("models_loaded", UNMEASURED),
                    ("inference_count_24h", inference_count),
                    ("avg_inference_ms", avg_inference_ms),
                    ("gpu_utilization_pct", UNMEASURED),
                    ("queue_depth", queue_depth),
                )
                if value is None
            ],
        }

    # ------------------------------------------------------------------
    # Error taxonomy
    # ------------------------------------------------------------------

    @staticmethod
    async def get_error_taxonomy(
        db: AsyncSession, hours: int = 24
    ) -> dict[str, Any]:
        """Categorise recorded errors by type and endpoint.

        Read from the ``errors_total`` counter. When nothing has been counted
        the breakdowns come back empty — which means "no errors observed", not
        "no data available"; ``observed`` distinguishes the two for the UI.
        """
        error_types = metrics_source.counter_by_label("errors_total", "type")
        by_endpoint = metrics_source.counter_by_label("errors_total", "endpoint")
        total = sum(error_types.values())

        # The counter carries no timestamps, so "last seen" is not derivable.
        top_errors = [
            {"error": etype, "count": count, "last_seen": UNMEASURED}
            for etype, count in sorted(
                error_types.items(), key=lambda x: x[1], reverse=True
            )
        ]

        return {
            "total_errors": total,
            "by_type": error_types,
            "by_endpoint": by_endpoint,
            "top_errors": top_errors,
            "observed": bool(error_types),
            "metrics_window": "process_lifetime",
            "requested_window_hours": hours,
        }

    # ------------------------------------------------------------------
    # Queue metrics
    # ------------------------------------------------------------------

    @staticmethod
    async def get_queue_metrics() -> dict[str, Any]:
        """Return Celery queue metrics.

        Tries ``celery.app.control.Inspect``; falls back to stub values.
        """
        try:
            from app.celery_app import celery_app  # type: ignore[import-untyped]

            inspector = celery_app.control.inspect()
            active = inspector.active() or {}
            reserved = inspector.reserved() or {}
            celery_active = sum(len(v) for v in active.values())
            celery_pending = sum(len(v) for v in reserved.values())
        except Exception:
            # Broker unreachable — say so instead of reporting a quiet queue.
            logger.warning("Queue metrics unavailable: could not inspect Celery")
            celery_active = UNMEASURED
            celery_pending = UNMEASURED

        return {
            "celery_active": celery_active,
            "celery_pending": celery_pending,
            # Celery's inspect API exposes no historical failure count.
            "celery_failed_24h": UNMEASURED,
            "unmeasured": [
                name
                for name, value in (
                    ("celery_active", celery_active),
                    ("celery_pending", celery_pending),
                    ("celery_failed_24h", UNMEASURED),
                )
                if value is None
            ],
        }
