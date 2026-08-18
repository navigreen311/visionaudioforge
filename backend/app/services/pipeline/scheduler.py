"""Pipeline scheduling — store and manage cron-based pipeline schedules."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduling import PipelineSchedule


class PipelineScheduler:
    """Manage cron-based pipeline scheduling.

    Schedules are rows in ``pipeline_schedules``. They used to be held in a
    per-instance dict: writes went to the pipeline's definition JSON but reads
    came from memory, so after a restart the service reported no schedules
    while the rows still existed, and each worker had its own view.

    Actual cron execution is still V2 (it needs Celery Beat); this service
    provides schedule CRUD and cron parsing.
    """

    @staticmethod
    def _serialise(row: PipelineSchedule) -> dict[str, Any]:
        return {
            "schedule_id": str(row.id),
            "pipeline_id": str(row.pipeline_id),
            "cron": row.cron,
            "enabled": row.enabled,
            "next_run": row.next_run.isoformat() if row.next_run else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def schedule(
        self,
        db: AsyncSession,
        pipeline_id: str,
        cron_expression: str,
        enabled: bool = True,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Create or update a schedule for a pipeline.

        Returns schedule metadata including the next calculated run time.
        """
        if not croniter.is_valid(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        now = datetime.now(timezone.utc)
        next_run: datetime = croniter(cron_expression, now).get_next(datetime)

        # One schedule per pipeline: re-scheduling replaces rather than
        # accumulating duplicates that would each fire.
        existing = (
            await db.execute(
                select(PipelineSchedule).where(
                    PipelineSchedule.pipeline_id == uuid.UUID(pipeline_id)
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            existing = PipelineSchedule(
                pipeline_id=uuid.UUID(pipeline_id),
                workspace_id=workspace_id,
            )
            db.add(existing)

        existing.cron = cron_expression
        existing.enabled = enabled
        existing.next_run = next_run
        if workspace_id is not None:
            existing.workspace_id = workspace_id

        await db.commit()
        await db.refresh(existing)
        return self._serialise(existing)

    async def unschedule(self, db: AsyncSession, schedule_id: str) -> bool:
        """Remove a schedule by ID. Returns True if found and removed."""
        row = (
            await db.execute(
                select(PipelineSchedule).where(
                    PipelineSchedule.id == uuid.UUID(schedule_id)
                )
            )
        ).scalar_one_or_none()

        if row is None:
            return False

        await db.delete(row)
        await db.commit()
        return True

    async def list_schedules(
        self, db: AsyncSession, workspace_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return all stored schedules, optionally filtered by workspace."""
        stmt = select(PipelineSchedule)
        if workspace_id is not None:
            stmt = stmt.where(PipelineSchedule.workspace_id == workspace_id)
        stmt = stmt.order_by(PipelineSchedule.created_at)

        rows = (await db.execute(stmt)).scalars().all()
        return [self._serialise(r) for r in rows]

    async def get_next_runs(
        self,
        db: AsyncSession,
        workspace_id: str | None = None,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Return upcoming runs within the next *hours* hours."""
        stmt = select(PipelineSchedule).where(PipelineSchedule.enabled.is_(True))
        if workspace_id is not None:
            stmt = stmt.where(PipelineSchedule.workspace_id == workspace_id)

        rows = (await db.execute(stmt)).scalars().all()

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours)
        upcoming: list[dict[str, Any]] = []

        for row in rows:
            cron = croniter(row.cron, now)
            next_run: datetime = cron.get_next(datetime)
            while next_run <= cutoff:
                upcoming.append(
                    {
                        "schedule_id": str(row.id),
                        "pipeline_id": str(row.pipeline_id),
                        "run_at": next_run.isoformat(),
                    }
                )
                next_run = cron.get_next(datetime)

        upcoming.sort(key=lambda r: r["run_at"])
        return upcoming
