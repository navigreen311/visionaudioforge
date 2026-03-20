"""CockpitDashboard — aggregated overview, zone status, timeline feed, and KPI metrics."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertStatus
from app.models.command_center import (
    CommandStream,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    OperatorShift,
    StreamStatus,
)
from app.models.event import Event

logger = logging.getLogger(__name__)

import uuid


class CockpitDashboard:
    """Provides aggregated dashboard data for a Command Center workspace."""

    @staticmethod
    async def get_overview(
        db: AsyncSession,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Top-level cockpit overview: streams, operators, incidents, alerts."""
        wid = uuid.UUID(workspace_id)
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)

        # Active streams
        streams_q = await db.execute(
            select(func.count(CommandStream.id))
            .where(CommandStream.workspace_id == wid)
        )
        active_streams = streams_q.scalar() or 0

        # Active operators
        ops_q = await db.execute(
            select(func.count(OperatorShift.id))
            .where(OperatorShift.workspace_id == wid, OperatorShift.is_active == 1)
        )
        active_operators = ops_q.scalar() or 0

        # Open incidents
        active_statuses = [IncidentStatus.active, IncidentStatus.assigned, IncidentStatus.escalated]
        inc_q = await db.execute(
            select(func.count(Incident.id))
            .where(Incident.workspace_id == wid, Incident.status.in_(active_statuses))
        )
        open_incidents = inc_q.scalar() or 0

        # Alerts in last 24h
        alerts_q = await db.execute(
            select(func.count(Alert.id))
            .where(Alert.workspace_id == wid, Alert.created_at >= day_ago)
        )
        alerts_24h = alerts_q.scalar() or 0

        # Stream health summary
        health_q = await db.execute(
            select(CommandStream.status, func.count(CommandStream.id))
            .where(CommandStream.workspace_id == wid)
            .group_by(CommandStream.status)
        )
        streams_health = {row[0].value: row[1] for row in health_q.all()}

        # System status heuristic
        if open_incidents == 0 and active_streams > 0:
            system_status = "healthy"
        elif open_incidents <= 3:
            system_status = "warning"
        else:
            system_status = "critical"

        return {
            "active_streams": active_streams,
            "active_operators": active_operators,
            "open_incidents": open_incidents,
            "alerts_24h": alerts_24h,
            "streams_health": streams_health,
            "system_status": system_status,
        }

    @staticmethod
    async def get_zone_status(
        db: AsyncSession,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        """Return per-zone breakdown of streams, incidents, and assigned operator."""
        wid = uuid.UUID(workspace_id)

        # Get zones from active shifts
        shifts_q = await db.execute(
            select(OperatorShift)
            .where(OperatorShift.workspace_id == wid, OperatorShift.is_active == 1)
        )
        shifts = shifts_q.scalars().all()

        zones: dict[str, dict[str, Any]] = {}
        for s in shifts:
            zone_name = s.zone_assignment or "unassigned"
            zones.setdefault(zone_name, {"zone": zone_name, "streams": 0, "incidents": 0, "operator": None})
            zones[zone_name]["operator"] = str(s.operator_id)

        # Count streams (all go to default zone if no zone mapping)
        streams_q = await db.execute(
            select(func.count(CommandStream.id))
            .where(CommandStream.workspace_id == wid)
        )
        total_streams = streams_q.scalar() or 0

        # Count active incidents
        active_statuses = [IncidentStatus.active, IncidentStatus.assigned, IncidentStatus.escalated]
        inc_q = await db.execute(
            select(func.count(Incident.id))
            .where(Incident.workspace_id == wid, Incident.status.in_(active_statuses))
        )
        total_incidents = inc_q.scalar() or 0

        if not zones:
            zones["default"] = {"zone": "default", "streams": 0, "incidents": 0, "operator": None}

        # Distribute streams and incidents evenly across zones for simplicity
        zone_list = list(zones.values())
        for i, z in enumerate(zone_list):
            z["streams"] = total_streams // len(zone_list) + (1 if i < total_streams % len(zone_list) else 0)
            z["incidents"] = total_incidents // len(zone_list) + (1 if i < total_incidents % len(zone_list) else 0)

        return zone_list

    @staticmethod
    async def get_timeline_feed(
        db: AsyncSession,
        workspace_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return recent events, alerts, and incidents in chronological order."""
        wid = uuid.UUID(workspace_id)

        # Recent events
        events_q = await db.execute(
            select(Event)
            .where(Event.workspace_id == wid)
            .order_by(Event.timestamp.desc())
            .limit(limit)
        )
        events = events_q.scalars().all()

        timeline = []
        for e in events:
            summary = e.payload.get("note", e.type) if isinstance(e.payload, dict) else e.type
            timeline.append({
                "id": str(e.id),
                "type": e.type,
                "summary": summary,
                "timestamp": e.timestamp.isoformat(),
                "payload": e.payload,
            })

        # Recent incidents (as timeline items)
        inc_q = await db.execute(
            select(Incident)
            .where(Incident.workspace_id == wid)
            .order_by(Incident.created_at.desc())
            .limit(limit)
        )
        incidents = inc_q.scalars().all()

        for i in incidents:
            timeline.append({
                "id": str(i.id),
                "type": "incident",
                "summary": f"[{i.severity.value.upper()}] {i.title}",
                "timestamp": i.created_at.isoformat(),
                "payload": {"status": i.status.value, "severity": i.severity.value},
            })

        # Sort by timestamp descending and limit
        timeline.sort(key=lambda x: x["timestamp"], reverse=True)
        return timeline[:limit]

    @staticmethod
    async def get_kpis(
        db: AsyncSession,
        workspace_id: str,
        period: str = "daily",
    ) -> dict[str, float]:
        """Calculate KPI metrics for the workspace."""
        wid = uuid.UUID(workspace_id)
        now = datetime.now(timezone.utc)

        period_hours = {"hourly": 1, "daily": 24, "weekly": 168, "monthly": 720}
        hours = period_hours.get(period, 24)
        since = now - timedelta(hours=hours)

        # Avg response time for resolved / assigned incidents in period
        avg_q = await db.execute(
            select(func.avg(Incident.response_time_s))
            .where(
                Incident.workspace_id == wid,
                Incident.created_at >= since,
                Incident.response_time_s.isnot(None),
            )
        )
        avg_response = avg_q.scalar() or 0.0

        # Resolution rate
        total_q = await db.execute(
            select(func.count(Incident.id))
            .where(Incident.workspace_id == wid, Incident.created_at >= since)
        )
        total = total_q.scalar() or 0

        resolved_q = await db.execute(
            select(func.count(Incident.id))
            .where(
                Incident.workspace_id == wid,
                Incident.created_at >= since,
                Incident.status == IncidentStatus.resolved,
            )
        )
        resolved = resolved_q.scalar() or 0
        resolution_rate = (resolved / total) if total > 0 else 1.0

        # False alarm rate (dismissed / total)
        dismissed_q = await db.execute(
            select(func.count(Incident.id))
            .where(
                Incident.workspace_id == wid,
                Incident.created_at >= since,
                Incident.status == IncidentStatus.dismissed,
            )
        )
        dismissed = dismissed_q.scalar() or 0
        false_alarm_rate = (dismissed / total) if total > 0 else 0.0

        # Uptime: ratio of connected streams vs total
        total_streams_q = await db.execute(
            select(func.count(CommandStream.id))
            .where(CommandStream.workspace_id == wid)
        )
        total_streams = total_streams_q.scalar() or 0

        connected_q = await db.execute(
            select(func.count(CommandStream.id))
            .where(CommandStream.workspace_id == wid, CommandStream.status == StreamStatus.connected)
        )
        connected = connected_q.scalar() or 0
        uptime_pct = (connected / total_streams * 100) if total_streams > 0 else 100.0

        return {
            "avg_response_time_s": round(float(avg_response), 2),
            "incident_resolution_rate": round(resolution_rate, 4),
            "false_alarm_rate": round(false_alarm_rate, 4),
            "uptime_pct": round(uptime_pct, 2),
        }
