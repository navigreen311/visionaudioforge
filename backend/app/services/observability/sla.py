"""SLA reporting service.

Defines standard SLA tiers, checks compliance, and generates periodic
SLA reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.observability import metrics_source

logger = logging.getLogger(__name__)

#: Marker used whenever a figure could not be measured. Callers/UI should render
#: this as "unknown", never as a zero or a passing value.
UNMEASURED: None = None

# ---------------------------------------------------------------------------
# Standard SLA tiers
# ---------------------------------------------------------------------------

STANDARD_SLAS: dict[str, dict[str, float]] = {
    "basic": {"uptime": 99.0, "latency": 1000, "error_rate": 0.05},
    "standard": {"uptime": 99.9, "latency": 500, "error_rate": 0.01},
    "premium": {"uptime": 99.99, "latency": 200, "error_rate": 0.001},
}


class SLAService:
    """Define, check and report on SLA compliance."""

    # ------------------------------------------------------------------
    # SLA definition helper
    # ------------------------------------------------------------------

    @staticmethod
    def define_sla(
        name: str,
        target_uptime: float = 99.9,
        max_latency_ms: float = 500,
        max_error_rate: float = 0.01,
    ) -> dict[str, Any]:
        """Create an SLA configuration dict."""
        return {
            "name": name,
            "target_uptime": target_uptime,
            "max_latency_ms": max_latency_ms,
            "max_error_rate": max_error_rate,
        }

    # ------------------------------------------------------------------
    # Compliance check
    # ------------------------------------------------------------------

    @staticmethod
    async def check_sla_compliance(
        db: AsyncSession,
        sla_config: dict[str, Any],
        period_hours: int = 24,
    ) -> dict[str, Any]:
        """Check measured metrics against the given SLA config.

        Values that cannot be measured are reported as ``None`` and listed in
        ``unmeasured``. Compliance **fails closed**: a report never claims the
        SLA was met on the strength of data that was never collected.
        """
        latency = metrics_source.average_request_latency_ms()
        errors = metrics_source.error_rate()

        # Uptime needs external probing (a blackbox exporter or synthetic
        # check); nothing in-process can attest to it, so it stays unmeasured
        # rather than being approximated.
        uptime_pct = UNMEASURED

        avg_latency_ms = round(latency.value, 2) if latency.observed else UNMEASURED
        error_rate = round(errors.value, 6) if errors.observed else UNMEASURED

        violations: list[str] = []
        unmeasured: list[str] = []

        if uptime_pct is None:
            unmeasured.append("uptime_pct")
        elif uptime_pct < sla_config["target_uptime"]:
            violations.append(
                f"Uptime {uptime_pct}% < target {sla_config['target_uptime']}%"
            )

        if avg_latency_ms is None:
            unmeasured.append("avg_latency_ms")
        elif avg_latency_ms > sla_config["max_latency_ms"]:
            violations.append(
                f"Latency {avg_latency_ms}ms > max {sla_config['max_latency_ms']}ms"
            )

        if error_rate is None:
            unmeasured.append("error_rate")
        elif error_rate > sla_config["max_error_rate"]:
            violations.append(
                f"Error rate {error_rate} > max {sla_config['max_error_rate']}"
            )

        if unmeasured:
            status = "insufficient_data"
            compliant = False
        else:
            status = "measured"
            compliant = len(violations) == 0

        return {
            "compliant": compliant,
            "status": status,
            "uptime_pct": uptime_pct,
            "avg_latency_ms": avg_latency_ms,
            "error_rate": error_rate,
            "violations": violations,
            "unmeasured": unmeasured,
            "period_hours": period_hours,
            "request_sample_count": errors.sample_count,
        }

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_sla_report(
        db: AsyncSession,
        period: str = "weekly",
    ) -> dict[str, Any]:
        """Generate a periodic SLA report.

        *period* can be ``'daily'``, ``'weekly'``, or ``'monthly'``.
        """
        now = datetime.now(timezone.utc)
        delta_map = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
        }
        delta = delta_map.get(period, timedelta(weeks=1))
        start = now - delta

        latency = metrics_source.average_request_latency_ms()

        # Only the mean is derivable from the current histogram configuration;
        # p50/p99 need quantile buckets that are not configured, and uptime and
        # incident counts have no recorded source at all. All are reported as
        # unmeasured instead of being synthesised.
        avg_latency_ms = round(latency.value, 2) if latency.observed else UNMEASURED

        unmeasured = [
            name
            for name, value in (
                ("uptime", UNMEASURED),
                ("latency_p50", UNMEASURED),
                ("latency_p99", UNMEASURED),
                ("incidents", UNMEASURED),
                ("avg_latency_ms", avg_latency_ms),
            )
            if value is None
        ]

        return {
            "period": period,
            "start": start.isoformat(),
            "end": now.isoformat(),
            "status": "insufficient_data" if unmeasured else "measured",
            "uptime": UNMEASURED,
            "latency_p50": UNMEASURED,
            "latency_p99": UNMEASURED,
            "avg_latency_ms": avg_latency_ms,
            "incidents": UNMEASURED,
            "unmeasured": unmeasured,
            # Fails closed: compliance is never asserted from absent data.
            "compliance": False,
            "request_sample_count": latency.sample_count,
        }
