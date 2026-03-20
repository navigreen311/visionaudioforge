"""Pipeline scheduling — store and manage cron-based pipeline schedules."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from croniter import croniter


class PipelineScheduler:
    """Manage cron-based pipeline scheduling.

    Schedules are stored in the Pipeline model's definition JSONB field
    under the ``schedule`` key.  Actual cron execution is V2 (requires
    Celery Beat); this service provides schedule CRUD and cron parsing.
    """

    def __init__(self, db_session: Any = None):
        self._db = db_session
        # In-memory store for when no DB session is available (testing/dev)
        self._schedules: dict[str, dict[str, Any]] = {}

    async def schedule(
        self,
        pipeline_id: str,
        cron_expression: str,
        enabled: bool = True,
    ) -> dict[str, Any]:
        """Create or update a schedule for a pipeline.

        Returns schedule metadata including the next calculated run time.
        """
        # Validate cron expression
        if not croniter.is_valid(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        schedule_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        cron = croniter(cron_expression, now)
        next_run: datetime = cron.get_next(datetime)

        schedule_data = {
            "schedule_id": schedule_id,
            "pipeline_id": pipeline_id,
            "cron": cron_expression,
            "enabled": enabled,
            "next_run": next_run.isoformat(),
            "created_at": now.isoformat(),
        }

        # Persist to DB if available
        if self._db is not None:
            from sqlalchemy import select

            from app.models.pipeline import Pipeline

            result = await self._db.execute(
                select(Pipeline).where(Pipeline.id == uuid.UUID(pipeline_id))
            )
            pipeline = result.scalar_one_or_none()
            if pipeline is not None:
                definition = dict(pipeline.definition or {})
                definition["schedule"] = schedule_data
                pipeline.definition = definition
                await self._db.commit()

        # Always store in memory for fast access
        self._schedules[schedule_id] = schedule_data
        return schedule_data

    async def unschedule(self, schedule_id: str) -> bool:
        """Remove a schedule by ID.  Returns True if found and removed."""
        if schedule_id in self._schedules:
            schedule = self._schedules.pop(schedule_id)

            # Remove from DB if available
            if self._db is not None:
                from sqlalchemy import select

                from app.models.pipeline import Pipeline

                pipeline_id = schedule["pipeline_id"]
                result = await self._db.execute(
                    select(Pipeline).where(Pipeline.id == uuid.UUID(pipeline_id))
                )
                pipeline = result.scalar_one_or_none()
                if pipeline is not None:
                    definition = dict(pipeline.definition or {})
                    definition.pop("schedule", None)
                    pipeline.definition = definition
                    await self._db.commit()

            return True
        return False

    async def list_schedules(self, workspace_id: str | None = None) -> list[dict[str, Any]]:
        """Return all stored schedules, optionally filtered by workspace."""
        # In the in-memory store we don't track workspace, so return all
        return list(self._schedules.values())

    async def get_next_runs(
        self,
        workspace_id: str | None = None,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Return upcoming runs within the next *hours* hours."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours)
        upcoming: list[dict[str, Any]] = []

        for schedule in self._schedules.values():
            if not schedule.get("enabled", True):
                continue
            cron_expr = schedule["cron"]
            cron = croniter(cron_expr, now)
            next_run: datetime = cron.get_next(datetime)
            while next_run <= cutoff:
                upcoming.append({
                    "schedule_id": schedule["schedule_id"],
                    "pipeline_id": schedule["pipeline_id"],
                    "run_at": next_run.isoformat(),
                })
                next_run = cron.get_next(datetime)

        upcoming.sort(key=lambda r: r["run_at"])
        return upcoming
