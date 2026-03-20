"""Investigation service — case management, evidence linking, and timeline queries."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event

logger = logging.getLogger(__name__)


class InvestigationService:
    """Manages investigation cases, evidence, notes, and timeline queries."""

    async def create_case(
        self,
        db: AsyncSession,
        name: str,
        description: str,
        workspace_id: UUID,
    ) -> Event:
        """Create a new investigation case (stored as Event with type='case')."""
        case = Event(
            id=uuid4(),
            type="case",
            source="investigation",
            workspace_id=workspace_id,
            payload={
                "name": name,
                "description": description,
                "status": "open",
            },
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
        return case

    async def add_evidence(
        self,
        db: AsyncSession,
        case_id: UUID,
        asset_id: UUID,
        notes: str,
        timestamp: Optional[datetime] = None,
    ) -> Event:
        """Link an asset as evidence to a case."""
        # Verify case exists
        result = await db.execute(select(Event).where(Event.id == case_id, Event.type == "case"))
        case = result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        evidence = Event(
            id=uuid4(),
            type="evidence",
            source="investigation",
            workspace_id=case.workspace_id,
            linked_asset_ids=[asset_id],
            payload={
                "case_id": str(case_id),
                "notes": notes,
            },
        )
        if timestamp:
            evidence.timestamp = timestamp
        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)
        return evidence

    async def get_timeline(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        start_time: datetime,
        end_time: datetime,
        event_types: Optional[list[str]] = None,
    ) -> list[Event]:
        """Query events in a workspace within a time range, ordered by timestamp."""
        stmt = (
            select(Event)
            .where(
                Event.workspace_id == workspace_id,
                Event.timestamp >= start_time,
                Event.timestamp <= end_time,
            )
            .order_by(Event.timestamp.asc())
        )
        if event_types:
            stmt = stmt.where(Event.type.in_(event_types))

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_case(self, db: AsyncSession, case_id: UUID) -> dict:
        """Get a case with all linked evidence and notes."""
        result = await db.execute(select(Event).where(Event.id == case_id, Event.type == "case"))
        case = result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        # Get linked evidence and notes
        evidence_result = await db.execute(
            select(Event)
            .where(Event.type.in_(["evidence", "note"]))
            .where(Event.workspace_id == case.workspace_id)
            .order_by(Event.timestamp.asc())
        )
        all_events = list(evidence_result.scalars().all())
        case_events = [
            e for e in all_events
            if e.payload and e.payload.get("case_id") == str(case_id)
        ]

        return {
            "case": case,
            "events": case_events,
            "evidence": [e for e in case_events if e.type == "evidence"],
            "notes": [e for e in case_events if e.type == "note"],
        }

    async def list_cases(self, db: AsyncSession, workspace_id: UUID) -> list[Event]:
        """List all cases in a workspace."""
        result = await db.execute(
            select(Event)
            .where(Event.workspace_id == workspace_id, Event.type == "case")
            .order_by(Event.timestamp.desc())
        )
        return list(result.scalars().all())

    async def add_note(
        self,
        db: AsyncSession,
        case_id: UUID,
        user_id: str,
        content: str,
    ) -> Event:
        """Add a note to a case."""
        result = await db.execute(select(Event).where(Event.id == case_id, Event.type == "case"))
        case = result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        note = Event(
            id=uuid4(),
            type="note",
            source="investigation",
            workspace_id=case.workspace_id,
            payload={
                "case_id": str(case_id),
                "user_id": user_id,
                "content": content,
            },
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note

    async def export_case(self, db: AsyncSession, case_id: UUID) -> dict:
        """Export a full case as a structured dictionary."""
        case_data = await self.get_case(db, case_id)
        case_event = case_data["case"]

        def _serialize_event(e: Event) -> dict:
            return {
                "id": str(e.id),
                "type": e.type,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "source": e.source,
                "payload": e.payload,
                "linked_asset_ids": [str(a) for a in (e.linked_asset_ids or [])],
            }

        return {
            "case": {
                "id": str(case_event.id),
                "name": case_event.payload.get("name"),
                "description": case_event.payload.get("description"),
                "status": case_event.payload.get("status"),
                "created_at": case_event.timestamp.isoformat() if case_event.timestamp else None,
            },
            "events": [_serialize_event(e) for e in case_data["events"]],
            "evidence": [_serialize_event(e) for e in case_data["evidence"]],
            "timeline": [_serialize_event(e) for e in case_data["events"]],
        }
