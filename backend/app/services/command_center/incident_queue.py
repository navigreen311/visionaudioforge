"""IncidentQueueService — live incident queue with severity sorting, assignment, and escalation."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command_center import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    OperatorShift,
)
from app.models.event import Event

logger = logging.getLogger(__name__)

# Severity ordering: critical first
_SEVERITY_SORT_ORDER = case(
    (Incident.severity == IncidentSeverity.critical, 0),
    (Incident.severity == IncidentSeverity.high, 1),
    (Incident.severity == IncidentSeverity.medium, 2),
    (Incident.severity == IncidentSeverity.low, 3),
    else_=4,
)


class IncidentQueueService:
    """Manages the live incident queue for a Command Center workspace."""

    @staticmethod
    async def get_queue(
        db: AsyncSession,
        workspace_id: str,
        status: str = "active",
    ) -> list[dict[str, Any]]:
        """Return incidents sorted by severity (critical first) then by time (oldest first)."""
        wid = uuid.UUID(workspace_id)

        # Map status filter
        status_filters = {
            "active": [IncidentStatus.active, IncidentStatus.assigned, IncidentStatus.escalated],
            "resolved": [IncidentStatus.resolved],
            "dismissed": [IncidentStatus.dismissed],
        }
        allowed = status_filters.get(status, [IncidentStatus(status)])

        result = await db.execute(
            select(Incident)
            .where(Incident.workspace_id == wid, Incident.status.in_(allowed))
            .order_by(_SEVERITY_SORT_ORDER, Incident.created_at.asc())
        )
        incidents = result.scalars().all()
        return [
            {
                "incident_id": str(i.id),
                "title": i.title,
                "severity": i.severity.value,
                "status": i.status.value,
                "assigned_to": str(i.assigned_to) if i.assigned_to else None,
                "escalation_level": i.escalation_level,
                "created_at": i.created_at.isoformat(),
            }
            for i in incidents
        ]

    @staticmethod
    async def assign_incident(
        db: AsyncSession,
        incident_id: str,
        operator_id: str,
    ) -> dict[str, Any]:
        """Assign an incident to an operator."""
        iid = uuid.UUID(incident_id)
        oid = uuid.UUID(operator_id)

        result = await db.execute(select(Incident).where(Incident.id == iid))
        incident = result.scalar_one_or_none()
        if incident is None:
            raise ValueError(f"Incident {incident_id} not found")

        now = datetime.now(timezone.utc)
        if incident.response_time_s is None:
            created = incident.created_at.replace(tzinfo=timezone.utc) if incident.created_at.tzinfo is None else incident.created_at
            incident.response_time_s = (now - created).total_seconds()

        incident.assigned_to = oid
        incident.status = IncidentStatus.assigned
        await db.commit()

        logger.info("Incident %s assigned to operator %s", incident_id, operator_id)
        return {
            "incident_id": str(incident.id),
            "status": incident.status.value,
            "assigned_to": str(incident.assigned_to),
        }

    @staticmethod
    async def escalate_incident(
        db: AsyncSession,
        incident_id: str,
        level: int,
    ) -> dict[str, Any]:
        """Escalate an incident to a higher level."""
        iid = uuid.UUID(incident_id)
        result = await db.execute(select(Incident).where(Incident.id == iid))
        incident = result.scalar_one_or_none()
        if incident is None:
            raise ValueError(f"Incident {incident_id} not found")

        incident.escalation_level = level
        incident.status = IncidentStatus.escalated
        await db.commit()

        logger.info("Incident %s escalated to level %d", incident_id, level)
        return {
            "incident_id": str(incident.id),
            "status": incident.status.value,
            "escalation_level": incident.escalation_level,
        }

    @staticmethod
    async def add_incident_note(
        db: AsyncSession,
        incident_id: str,
        operator_id: str,
        note: str,
    ) -> dict[str, Any]:
        """Add an operator note to an incident as an Event record."""
        iid = uuid.UUID(incident_id)

        # Verify incident exists
        result = await db.execute(select(Incident).where(Incident.id == iid))
        incident = result.scalar_one_or_none()
        if incident is None:
            raise ValueError(f"Incident {incident_id} not found")

        event = Event(
            type="incident_note",
            payload={"incident_id": incident_id, "operator_id": operator_id, "note": note},
            source="command_center",
            workspace_id=incident.workspace_id,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        return {
            "event_id": str(event.id),
            "incident_id": incident_id,
            "operator_id": operator_id,
            "note": note,
            "timestamp": event.timestamp.isoformat(),
        }

    @staticmethod
    async def get_queue_stats(
        db: AsyncSession,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Return aggregate stats for the incident queue."""
        wid = uuid.UUID(workspace_id)
        now = datetime.now(timezone.utc)

        active_statuses = [IncidentStatus.active, IncidentStatus.assigned, IncidentStatus.escalated]

        # Total active
        total_q = await db.execute(
            select(func.count(Incident.id))
            .where(Incident.workspace_id == wid, Incident.status.in_(active_statuses))
        )
        total_active = total_q.scalar() or 0

        # By severity
        sev_q = await db.execute(
            select(Incident.severity, func.count(Incident.id))
            .where(Incident.workspace_id == wid, Incident.status.in_(active_statuses))
            .group_by(Incident.severity)
        )
        by_severity = {row[0].value: row[1] for row in sev_q.all()}

        # Avg response time
        avg_q = await db.execute(
            select(func.avg(Incident.response_time_s))
            .where(Incident.workspace_id == wid, Incident.response_time_s.isnot(None))
        )
        avg_response = avg_q.scalar() or 0.0

        # Unassigned
        unassigned_q = await db.execute(
            select(func.count(Incident.id))
            .where(
                Incident.workspace_id == wid,
                Incident.status == IncidentStatus.active,
                Incident.assigned_to.is_(None),
            )
        )
        unassigned = unassigned_q.scalar() or 0

        # Oldest unresolved
        oldest_q = await db.execute(
            select(func.min(Incident.created_at))
            .where(Incident.workspace_id == wid, Incident.status.in_(active_statuses))
        )
        oldest_ts = oldest_q.scalar()
        if oldest_ts:
            oldest_ts = oldest_ts.replace(tzinfo=timezone.utc) if oldest_ts.tzinfo is None else oldest_ts
            oldest_age = (now - oldest_ts).total_seconds()
        else:
            oldest_age = 0.0

        return {
            "total_active": total_active,
            "by_severity": by_severity,
            "avg_response_time_s": round(float(avg_response), 2),
            "unassigned": unassigned,
            "oldest_unresolved_age_s": round(oldest_age, 2),
        }

    @staticmethod
    async def auto_assign(
        db: AsyncSession,
        workspace_id: str,
    ) -> dict[str, int]:
        """Round-robin assign unassigned incidents to active operators."""
        wid = uuid.UUID(workspace_id)

        # Get active operators
        ops_q = await db.execute(
            select(OperatorShift.operator_id)
            .where(OperatorShift.workspace_id == wid, OperatorShift.is_active == 1)
            .order_by(OperatorShift.start_time)
        )
        operators = [row[0] for row in ops_q.all()]
        if not operators:
            return {"assigned": 0}

        # Get unassigned incidents
        inc_q = await db.execute(
            select(Incident)
            .where(
                Incident.workspace_id == wid,
                Incident.status == IncidentStatus.active,
                Incident.assigned_to.is_(None),
            )
            .order_by(_SEVERITY_SORT_ORDER, Incident.created_at.asc())
        )
        incidents = inc_q.scalars().all()

        assigned_count = 0
        now = datetime.now(timezone.utc)
        for idx, incident in enumerate(incidents):
            op_id = operators[idx % len(operators)]
            incident.assigned_to = op_id
            incident.status = IncidentStatus.assigned
            if incident.response_time_s is None:
                created = incident.created_at.replace(tzinfo=timezone.utc) if incident.created_at.tzinfo is None else incident.created_at
                incident.response_time_s = (now - created).total_seconds()
            assigned_count += 1

        await db.commit()
        logger.info("Auto-assigned %d incidents in workspace %s", assigned_count, workspace_id)
        return {"assigned": assigned_count}
