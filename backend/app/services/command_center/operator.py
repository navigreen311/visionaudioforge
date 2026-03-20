"""OperatorService — shift management, stream pinning, and action audit logging."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command_center import (
    CommandStream,
    OperatorActionLog,
    OperatorShift,
)

logger = logging.getLogger(__name__)


class OperatorService:
    """Manages operator shifts, stream focus, and audit logging."""

    # ------------------------------------------------------------------
    # Shift management
    # ------------------------------------------------------------------

    @staticmethod
    async def create_shift(
        db: AsyncSession,
        workspace_id: str,
        operator_id: str,
        start_time: datetime,
        end_time: datetime,
        zone_assignment: Optional[str] = None,
    ) -> dict[str, str]:
        """Create a new operator shift."""
        shift = OperatorShift(
            workspace_id=uuid.UUID(workspace_id),
            operator_id=uuid.UUID(operator_id),
            start_time=start_time,
            end_time=end_time,
            zone_assignment=zone_assignment,
            is_active=1,
        )
        db.add(shift)
        await db.commit()
        await db.refresh(shift)
        logger.info("Shift %s created for operator %s", shift.id, operator_id)
        return {"shift_id": str(shift.id)}

    @staticmethod
    async def end_shift(
        db: AsyncSession,
        shift_id: str,
        handoff_notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """End an active shift and record handoff notes."""
        sid = uuid.UUID(shift_id)
        result = await db.execute(select(OperatorShift).where(OperatorShift.id == sid))
        shift = result.scalar_one_or_none()
        if shift is None:
            raise ValueError(f"Shift {shift_id} not found")

        now = datetime.now(timezone.utc)
        duration_h = (now - shift.start_time.replace(tzinfo=timezone.utc)).total_seconds() / 3600.0

        shift.is_active = 0
        shift.end_time = now
        shift.handoff_notes = handoff_notes
        await db.commit()

        logger.info("Shift %s ended (%.1f h, %d events)", shift_id, duration_h, shift.events_handled)
        return {
            "shift_id": str(shift.id),
            "duration_h": round(duration_h, 2),
            "events_handled": shift.events_handled,
        }

    @staticmethod
    async def get_active_shift(
        db: AsyncSession,
        workspace_id: str,
        operator_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get the current active shift for an operator in a workspace."""
        result = await db.execute(
            select(OperatorShift).where(
                OperatorShift.workspace_id == uuid.UUID(workspace_id),
                OperatorShift.operator_id == uuid.UUID(operator_id),
                OperatorShift.is_active == 1,
            )
        )
        shift = result.scalar_one_or_none()
        if shift is None:
            return None
        return {
            "shift_id": str(shift.id),
            "operator_id": str(shift.operator_id),
            "start_time": shift.start_time.isoformat(),
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "zone_assignment": shift.zone_assignment,
            "is_active": bool(shift.is_active),
            "events_handled": shift.events_handled,
        }

    @staticmethod
    async def list_shifts(
        db: AsyncSession,
        workspace_id: str,
        date: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List shifts for a workspace, optionally filtered by date."""
        wid = uuid.UUID(workspace_id)
        query = select(OperatorShift).where(OperatorShift.workspace_id == wid)

        if date:
            day = datetime.fromisoformat(date).date()
            query = query.where(func.date(OperatorShift.start_time) == day)

        query = query.order_by(OperatorShift.start_time.desc())
        result = await db.execute(query)
        shifts = result.scalars().all()
        return [
            {
                "shift_id": str(s.id),
                "operator_id": str(s.operator_id),
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "zone_assignment": s.zone_assignment,
                "is_active": bool(s.is_active),
                "handoff_notes": s.handoff_notes,
                "events_handled": s.events_handled,
            }
            for s in shifts
        ]

    # ------------------------------------------------------------------
    # Stream focus controls
    # ------------------------------------------------------------------

    @staticmethod
    async def pin_stream(
        db: AsyncSession,
        workspace_id: str,
        stream_id: str,
        operator_id: str,
    ) -> dict[str, str]:
        """Mark a stream as the operator's primary focus."""
        wid = uuid.UUID(workspace_id)
        sid = uuid.UUID(stream_id)
        oid = uuid.UUID(operator_id)

        # Unpin any previously pinned stream for this operator
        await db.execute(
            update(CommandStream)
            .where(CommandStream.workspace_id == wid, CommandStream.pinned_by == oid)
            .values(pinned_by=None)
        )
        # Pin the target stream
        await db.execute(
            update(CommandStream)
            .where(CommandStream.workspace_id == wid, CommandStream.id == sid)
            .values(pinned_by=oid)
        )
        await db.commit()
        return {"status": "pinned", "stream_id": stream_id, "operator_id": operator_id}

    @staticmethod
    async def set_priority_stream(
        db: AsyncSession,
        workspace_id: str,
        stream_id: str,
    ) -> dict[str, str]:
        """Set one stream as the enlarged primary view, clearing others."""
        wid = uuid.UUID(workspace_id)
        sid = uuid.UUID(stream_id)

        # Clear existing priority
        await db.execute(
            update(CommandStream)
            .where(CommandStream.workspace_id == wid)
            .values(is_priority=0)
        )
        # Set new priority
        await db.execute(
            update(CommandStream)
            .where(CommandStream.workspace_id == wid, CommandStream.id == sid)
            .values(is_priority=1)
        )
        await db.commit()
        return {"status": "priority_set", "stream_id": stream_id}

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    @staticmethod
    async def operator_action_log(
        db: AsyncSession,
        operator_id: str,
        action: str,
        details: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Record an operator action for audit purposes."""
        log_entry = OperatorActionLog(
            operator_id=uuid.UUID(operator_id),
            action=action,
            details=details,
        )
        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        return {
            "log_id": str(log_entry.id),
            "operator_id": operator_id,
            "action": action,
            "timestamp": log_entry.timestamp.isoformat(),
        }
