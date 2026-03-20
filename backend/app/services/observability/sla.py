"""SLA reporting service.

Defines standard SLA tiers, checks compliance, and generates periodic
SLA reports.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

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
        """Check current metrics against the given SLA config.

        Returns a dict with ``compliant``, measured values, and any
        violations.
        """
        # V1: simulated metrics — replace with real Prometheus / DB queries
        uptime_pct = round(random.uniform(99.0, 100.0), 4)
        avg_latency_ms = round(random.uniform(30, 300), 2)
        error_rate = round(random.uniform(0.0, 0.03), 4)

        violations: list[str] = []
        if uptime_pct < sla_config["target_uptime"]:
            violations.append(
                f"Uptime {uptime_pct}% < target {sla_config['target_uptime']}%"
            )
        if avg_latency_ms > sla_config["max_latency_ms"]:
            violations.append(
                f"Latency {avg_latency_ms}ms > max {sla_config['max_latency_ms']}ms"
            )
        if error_rate > sla_config["max_error_rate"]:
            violations.append(
                f"Error rate {error_rate} > max {sla_config['max_error_rate']}"
            )

        return {
            "compliant": len(violations) == 0,
            "uptime_pct": uptime_pct,
            "avg_latency_ms": avg_latency_ms,
            "error_rate": error_rate,
            "violations": violations,
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

        # V1: simulated report data
        uptime = round(random.uniform(99.5, 100.0), 4)
        latency_p50 = round(random.uniform(30, 150), 2)
        latency_p99 = round(latency_p50 * random.uniform(3, 6), 2)
        incidents = random.randint(0, 5)

        return {
            "period": period,
            "start": start.isoformat(),
            "end": now.isoformat(),
            "uptime": uptime,
            "latency_p50": latency_p50,
            "latency_p99": latency_p99,
            "incidents": incidents,
            "compliance": uptime >= 99.9 and latency_p99 < 500,
        }
