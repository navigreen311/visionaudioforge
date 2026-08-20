"""Dashboard API routes — aggregate stats and recent activity.

This is the first screen anyone sees, so every number here is a real query.
Counts are point-in-time; the ``*_history`` sparklines are daily buckets over
the requested range, derived from each record's ``created_at``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.alert import Alert, AlertStatus
from app.models.asset import Asset
from app.models.command_center import CommandStream, Incident, StreamStatus
from app.models.model_registry import ModelRecord, ModelStatus
from app.models.pipeline import Pipeline, PipelineRun

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    active_streams: int = 0
    streams_history: list[int] = []
    models_production: int = 0
    models_history: list[int] = []
    open_alerts: int = 0
    alerts_history: list[int] = []
    total_assets: int = 0
    assets_history: list[int] = []


class ActivityItem(BaseModel):
    type: str
    message: str
    timestamp: str
    severity: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A constant, not state: how many daily buckets each range selector means.
# The dashboard's numbers come from real queries against alerts, assets,
# streams and models; there is no cache here to persist.
_RANGE_LENGTHS: dict[str, int] = {
    "7d": 7,
    "14d": 14,
    "30d": 30,
}

# Registry states that mean "serving traffic". `deployed` and `serving` used to
# be listed here too, but neither is a member of the modelstatus enum — against
# a String column they simply matched nothing, and once the column was declared
# as the enum it actually is, naming them made the query fail outright.
_PRODUCTION_STATUSES = (ModelStatus.production,)

# Alert states that still need a human.
_OPEN_ALERT_STATUSES = (AlertStatus.new, AlertStatus.acknowledged)


def _range_days(range_key: str) -> int:
    return _RANGE_LENGTHS.get(range_key, 7)


def _scoped(query, model, workspace_id: UUID | None):
    """Restrict a query to one workspace when a workspace is known.

    Workspace comes in as an argument rather than from a session dependency —
    the authenticated-workspace dependency lands on a separate branch.
    """
    if workspace_id is None:
        return query
    return query.where(model.workspace_id == workspace_id)


async def _count(
    db: AsyncSession, model, workspace_id: UUID | None, *conditions
) -> int:
    """Count rows of ``model`` matching ``conditions``, workspace-scoped."""
    query = select(func.count()).select_from(model)
    for condition in conditions:
        query = query.where(condition)
    result = await db.execute(_scoped(query, model, workspace_id))
    return int(result.scalar() or 0)


async def _daily_history(
    db: AsyncSession,
    model,
    workspace_id: UUID | None,
    days: int,
    *conditions,
) -> list[int]:
    """Return per-day creation counts for the last ``days`` days, oldest first."""
    start = datetime.now(timezone.utc) - timedelta(days=days - 1)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)

    # date() on a timestamptz converts using the *server's* timezone, while the
    # bucket list below is built from UTC dates. On a database whose timezone
    # is not UTC the two disagree and today's rows land in a bucket that is not
    # in the range at all, so the history read as all zeros.
    day = func.date(func.timezone("UTC", model.created_at))
    query = select(day, func.count()).where(model.created_at >= start)
    for condition in conditions:
        query = query.where(condition)
    query = _scoped(query, model, workspace_id).group_by(day)

    result = await db.execute(query)
    counts = {_as_date(bucket): int(total) for bucket, total in result.all()}

    first_day = start.date()
    return [counts.get(first_day + timedelta(days=i), 0) for i in range(days)]


def _as_date(value: Any) -> date | None:
    """Normalise whatever the driver returns for ``date(created_at)``."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else datetime.now(timezone.utc).isoformat()


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    range: str = Query("7d", alias="range"),
    workspace_id: UUID | None = Query(None, description="Scope stats to one workspace"),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """Aggregate dashboard statistics over the requested range."""
    days = _range_days(range)

    active_streams = await _count(
        db, CommandStream, workspace_id, CommandStream.status == StreamStatus.connected
    )
    models_production = await _count(
        db, ModelRecord, workspace_id, ModelRecord.status.in_(_PRODUCTION_STATUSES)
    )
    open_alerts = await _count(
        db, Alert, workspace_id, Alert.status.in_(_OPEN_ALERT_STATUSES)
    )
    total_assets = await _count(db, Asset, workspace_id)

    return DashboardStats(
        active_streams=active_streams,
        streams_history=await _daily_history(db, CommandStream, workspace_id, days),
        models_production=models_production,
        models_history=await _daily_history(
            db,
            ModelRecord,
            workspace_id,
            days,
            ModelRecord.status.in_(_PRODUCTION_STATUSES),
        ),
        open_alerts=open_alerts,
        alerts_history=await _daily_history(db, Alert, workspace_id, days),
        total_assets=total_assets,
        assets_history=await _daily_history(db, Asset, workspace_id, days),
    )


@router.get("/activity", response_model=list[ActivityItem])
async def dashboard_activity(
    limit: int = Query(20, ge=1, le=100),
    workspace_id: UUID | None = Query(None, description="Scope activity to one workspace"),
    db: AsyncSession = Depends(get_db),
) -> list[ActivityItem]:
    """Recent activity across alerts, assets, models, pipelines and streams.

    Each source contributes up to ``limit`` rows; the merged feed is sorted
    newest-first and truncated to ``limit``.
    """
    items: list[ActivityItem] = []
    items += await _recent_alerts(db, workspace_id, limit)
    items += await _recent_assets(db, workspace_id, limit)
    items += await _recent_models(db, workspace_id, limit)
    items += await _recent_pipeline_runs(db, workspace_id, limit)
    items += await _recent_streams(db, workspace_id, limit)
    items += await _recent_incidents(db, workspace_id, limit)

    items.sort(key=lambda item: item.timestamp, reverse=True)
    return items[:limit]


# ---------------------------------------------------------------------------
# Activity sources
#
# Types match the console's ActivityFeed colour map: capture, alert, pipeline,
# model, upload, search.
# ---------------------------------------------------------------------------

async def _recent(
    db: AsyncSession, query, model, workspace_id: UUID | None, limit: int
) -> Sequence[Any]:
    query = _scoped(query, model, workspace_id)
    result = await db.execute(query.order_by(model.created_at.desc()).limit(limit))
    return result.all()


async def _recent_alerts(
    db: AsyncSession, workspace_id: UUID | None, limit: int
) -> list[ActivityItem]:
    rows = await _recent(
        db,
        select(Alert.severity, Alert.status, Alert.created_at, Alert.payload),
        Alert,
        workspace_id,
        limit,
    )
    items = []
    for severity, status, created_at, payload in rows:
        detail = (payload or {}).get("message") if isinstance(payload, dict) else None
        items.append(
            ActivityItem(
                type="alert",
                message=detail or f"{_enum_value(severity).title()} alert {_enum_value(status)}",
                timestamp=_iso(created_at),
                severity=_enum_value(severity),
            )
        )
    return items


async def _recent_assets(
    db: AsyncSession, workspace_id: UUID | None, limit: int
) -> list[ActivityItem]:
    rows = await _recent(
        db,
        select(Asset.filename, Asset.type, Asset.created_at),
        Asset,
        workspace_id,
        limit,
    )
    return [
        ActivityItem(
            type="upload",
            message=f"Uploaded {_enum_value(asset_type)} '{filename}'",
            timestamp=_iso(created_at),
        )
        for filename, asset_type, created_at in rows
    ]


async def _recent_models(
    db: AsyncSession, workspace_id: UUID | None, limit: int
) -> list[ActivityItem]:
    rows = await _recent(
        db,
        select(
            ModelRecord.name,
            ModelRecord.version,
            ModelRecord.status,
            ModelRecord.created_at,
        ),
        ModelRecord,
        workspace_id,
        limit,
    )
    return [
        ActivityItem(
            type="model",
            message=f"Model '{name}' v{version} is {status}",
            timestamp=_iso(created_at),
        )
        for name, version, status, created_at in rows
    ]


async def _recent_pipeline_runs(
    db: AsyncSession, workspace_id: UUID | None, limit: int
) -> list[ActivityItem]:
    """Pipeline runs carry no workspace column — scope through their pipeline."""
    query = (
        select(Pipeline.name, PipelineRun.status, PipelineRun.started_at)
        .join(Pipeline, Pipeline.id == PipelineRun.pipeline_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
    )
    if workspace_id is not None:
        query = query.where(Pipeline.workspace_id == workspace_id)

    result = await db.execute(query)
    return [
        ActivityItem(
            type="pipeline",
            message=f"Pipeline '{name}' run {_enum_value(status)}",
            timestamp=_iso(started_at),
            severity="high" if _enum_value(status) == "failed" else None,
        )
        for name, status, started_at in result.all()
    ]


async def _recent_streams(
    db: AsyncSession, workspace_id: UUID | None, limit: int
) -> list[ActivityItem]:
    rows = await _recent(
        db,
        select(CommandStream.name, CommandStream.status, CommandStream.created_at),
        CommandStream,
        workspace_id,
        limit,
    )
    return [
        ActivityItem(
            type="capture",
            message=f"Stream '{name}' is {_enum_value(status)}",
            timestamp=_iso(created_at),
        )
        for name, status, created_at in rows
    ]


async def _recent_incidents(
    db: AsyncSession, workspace_id: UUID | None, limit: int
) -> list[ActivityItem]:
    rows = await _recent(
        db,
        select(
            Incident.title,
            Incident.severity,
            Incident.status,
            Incident.created_at,
        ),
        Incident,
        workspace_id,
        limit,
    )
    return [
        ActivityItem(
            type="alert",
            message=f"Incident '{title}' {_enum_value(status)}",
            timestamp=_iso(created_at),
            severity=_enum_value(severity),
        )
        for title, severity, status, created_at in rows
    ]
