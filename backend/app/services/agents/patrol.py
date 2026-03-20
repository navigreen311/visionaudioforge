"""Autonomous patrol agent — periodic system health and operational checks."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PatrolFinding(TypedDict):
    check: str
    status: str  # "ok" | "warning" | "critical"
    message: str
    timestamp: str


class PatrolAgent:
    """Runs periodic patrol cycles to monitor system health and operations."""

    def __init__(
        self,
        agent_id: str,
        workspace_id: str,
        check_interval_s: int = 60,
    ) -> None:
        self.agent_id = agent_id
        self.workspace_id = workspace_id
        self.check_interval_s = check_interval_s
        self._task: asyncio.Task | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    # ------------------------------------------------------------------
    # Patrol checks
    # ------------------------------------------------------------------

    async def _check_system_health(self) -> PatrolFinding:
        """Check DB and Redis connectivity."""
        now = datetime.now(timezone.utc).isoformat()
        issues: list[str] = []

        # Database
        try:
            from sqlalchemy import text

            from app.database import async_session_factory

            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            issues.append(f"database: {exc}")

        # Redis
        try:
            import redis.asyncio as aioredis

            from app.config import settings

            r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            await r.ping()
            await r.aclose()
        except Exception as exc:
            issues.append(f"redis: {exc}")

        if issues:
            return PatrolFinding(
                check="system_health",
                status="critical",
                message=f"Service issues detected: {'; '.join(issues)}",
                timestamp=now,
            )
        return PatrolFinding(
            check="system_health",
            status="ok",
            message="All core services healthy.",
            timestamp=now,
        )

    async def _check_unacknowledged_alerts(self) -> PatrolFinding:
        """Count unacknowledged alerts — warn if > 10."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            from app.database import async_session_factory
            from app.models.alert import Alert, AlertStatus

            async with async_session_factory() as session:
                count = (
                    await session.execute(
                        select(func.count()).select_from(Alert).where(Alert.status == AlertStatus.new)
                    )
                ).scalar() or 0

            if count > 10:
                return PatrolFinding(
                    check="unacknowledged_alerts",
                    status="warning",
                    message=f"{count} unacknowledged alerts found (threshold: 10).",
                    timestamp=now,
                )
            return PatrolFinding(
                check="unacknowledged_alerts",
                status="ok",
                message=f"{count} unacknowledged alert(s). Within threshold.",
                timestamp=now,
            )
        except Exception as exc:
            return PatrolFinding(
                check="unacknowledged_alerts",
                status="warning",
                message=f"Could not check alerts: {exc}",
                timestamp=now,
            )

    async def _check_model_drift(self) -> PatrolFinding:
        """Check if any model has been in staging > 7 days without promotion."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            from app.database import async_session_factory
            from app.models.model_registry import ModelRecord

            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            async with async_session_factory() as session:
                stmt = select(ModelRecord).where(
                    ModelRecord.status == "staging",
                    ModelRecord.updated_at <= cutoff,
                )
                result = await session.execute(stmt)
                stale_models = result.scalars().all()

            if stale_models:
                names = [f"{m.name}@{m.version}" for m in stale_models]
                return PatrolFinding(
                    check="model_drift",
                    status="warning",
                    message=f"{len(stale_models)} model(s) in staging > 7 days: {', '.join(names[:5])}",
                    timestamp=now,
                )
            return PatrolFinding(
                check="model_drift",
                status="ok",
                message="No stale staging models detected.",
                timestamp=now,
            )
        except Exception as exc:
            return PatrolFinding(
                check="model_drift",
                status="warning",
                message=f"Could not check model drift: {exc}",
                timestamp=now,
            )

    async def _check_storage_growth(self) -> PatrolFinding:
        """Estimate asset count as a proxy for storage growth."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            from app.database import async_session_factory
            from app.models.asset import Asset

            async with async_session_factory() as session:
                total = (
                    await session.execute(select(func.count()).select_from(Asset))
                ).scalar() or 0

                # Count assets added in last 24h
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                recent = (
                    await session.execute(
                        select(func.count())
                        .select_from(Asset)
                        .where(Asset.created_at >= cutoff)
                    )
                ).scalar() or 0

            return PatrolFinding(
                check="storage_growth",
                status="ok",
                message=f"Total assets: {total}. Added in last 24h: {recent}.",
                timestamp=now,
            )
        except Exception as exc:
            return PatrolFinding(
                check="storage_growth",
                status="warning",
                message=f"Could not check storage: {exc}",
                timestamp=now,
            )

    async def _check_queue_depth(self) -> PatrolFinding:
        """Check Celery queue depth via Redis if accessible."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            import redis.asyncio as aioredis

            from app.config import settings

            r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            queue_len = await r.llen("celery")
            await r.aclose()

            status = "ok"
            if queue_len > 100:
                status = "warning"
            if queue_len > 500:
                status = "critical"

            return PatrolFinding(
                check="queue_depth",
                status=status,
                message=f"Celery queue depth: {queue_len}.",
                timestamp=now,
            )
        except Exception as exc:
            return PatrolFinding(
                check="queue_depth",
                status="ok",
                message=f"Queue check unavailable (may be normal): {exc}",
                timestamp=now,
            )

    # ------------------------------------------------------------------
    # Patrol cycle
    # ------------------------------------------------------------------

    async def run_patrol_cycle(self) -> list[PatrolFinding]:
        """Run all patrol checks and return findings."""
        findings: list[PatrolFinding] = []

        checks = [
            self._check_system_health,
            self._check_unacknowledged_alerts,
            self._check_model_drift,
            self._check_storage_growth,
            self._check_queue_depth,
        ]

        for check_fn in checks:
            try:
                finding = await check_fn()
                findings.append(finding)
            except Exception as exc:
                findings.append(
                    PatrolFinding(
                        check=check_fn.__name__.replace("_check_", ""),
                        status="warning",
                        message=f"Check failed unexpectedly: {exc}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _patrol_loop(self, db_factory) -> None:
        """Internal loop that runs patrol cycles periodically."""
        while self._running:
            try:
                findings = await self.run_patrol_cycle()

                # Store findings as Events
                try:
                    async with db_factory() as session:
                        from app.models.event import Event

                        for finding in findings:
                            event = Event(
                                type="patrol_finding",
                                payload={
                                    "agent_id": self.agent_id,
                                    "check": finding["check"],
                                    "status": finding["status"],
                                    "message": finding["message"],
                                },
                                source="patrol",
                                workspace_id=uuid.UUID(self.workspace_id)
                                if isinstance(self.workspace_id, str)
                                else self.workspace_id,
                            )
                            session.add(event)
                        await session.commit()
                except Exception as exc:
                    logger.warning("Failed to store patrol findings: %s", exc)

                logger.info(
                    "Patrol cycle complete: %d findings (%d warnings, %d critical)",
                    len(findings),
                    sum(1 for f in findings if f["status"] == "warning"),
                    sum(1 for f in findings if f["status"] == "critical"),
                )

            except Exception as exc:
                logger.exception("Patrol cycle error: %s", exc)

            await asyncio.sleep(self.check_interval_s)

    async def start_patrol(self, db_factory=None) -> None:
        """Launch periodic patrol in the background."""
        if self.is_running:
            return

        if db_factory is None:
            from app.database import async_session_factory

            db_factory = async_session_factory

        self._running = True
        self._task = asyncio.create_task(self._patrol_loop(db_factory))
        logger.info("Patrol started for agent %s", self.agent_id)

    async def stop_patrol(self) -> None:
        """Stop the patrol loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Patrol stopped for agent %s", self.agent_id)

    async def get_patrol_report(
        self,
        db: AsyncSession,
        hours: int = 24,
    ) -> dict:
        """Get patrol findings from the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = (
            select(Event)
            .where(
                Event.type == "patrol_finding",
                Event.payload["agent_id"].as_string() == self.agent_id,
                Event.timestamp >= cutoff,
            )
            .order_by(Event.timestamp.desc())
        )
        result = await db.execute(stmt)
        events = result.scalars().all()

        findings = []
        warnings = 0
        critical = 0

        for e in events:
            payload = e.payload or {}
            status = payload.get("status", "ok")
            if status == "warning":
                warnings += 1
            elif status == "critical":
                critical += 1
            findings.append({
                "check": payload.get("check", ""),
                "status": status,
                "message": payload.get("message", ""),
                "timestamp": e.timestamp.isoformat() if e.timestamp else "",
            })

        return {
            "findings": findings,
            "checks_run": len(findings),
            "warnings": warnings,
            "critical": critical,
        }


# ---------------------------------------------------------------------------
# Singleton registry for active patrol agents
# ---------------------------------------------------------------------------

_active_patrols: dict[str, PatrolAgent] = {}


def get_patrol_agent(agent_id: str, workspace_id: str = "00000000-0000-0000-0000-000000000000") -> PatrolAgent:
    """Get or create a PatrolAgent for the given agent_id."""
    if agent_id not in _active_patrols:
        _active_patrols[agent_id] = PatrolAgent(agent_id, workspace_id)
    return _active_patrols[agent_id]
