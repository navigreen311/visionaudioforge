"""Report drafting service — auto-generate, export, and sign investigation reports."""

import hashlib
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event

logger = logging.getLogger(__name__)


class ReportService:
    """Auto-generates investigation reports from case data."""

    async def _get_case_data(self, db: AsyncSession, case_id: UUID) -> dict:
        """Internal helper to load full case context."""
        result = await db.execute(
            select(Event).where(Event.id == case_id, Event.type == "case")
        )
        case = result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        # Get all events linked to this case
        events_result = await db.execute(
            select(Event)
            .where(Event.workspace_id == case.workspace_id)
            .order_by(Event.timestamp.asc())
        )
        all_events = list(events_result.scalars().all())
        case_events = [
            e for e in all_events
            if e.payload and e.payload.get("case_id") == str(case_id)
        ]

        return {
            "case": case,
            "evidence": [e for e in case_events if e.type == "evidence"],
            "notes": [e for e in case_events if e.type == "note"],
            "comments": [e for e in case_events if e.type == "comment"],
            "checkpoints": [e for e in case_events if e.type == "checkpoint"],
            "all_events": case_events,
        }

    async def draft_report(self, db: AsyncSession, case_id: UUID) -> dict:
        """Auto-generate a report from case data.

        Builds sections from case name, evidence list, timeline events,
        and investigator notes.
        """
        data = await self._get_case_data(db, case_id)
        case = data["case"]
        payload = case.payload or {}

        title = f"Investigation Report: {payload.get('name', 'Untitled Case')}"

        # Build sections
        sections = []

        # Overview section
        sections.append({
            "heading": "Overview",
            "content": payload.get("description", "No description provided."),
        })

        # Evidence section
        evidence_items = data["evidence"]
        if evidence_items:
            evidence_lines = []
            for e in evidence_items:
                ep = e.payload or {}
                ts = e.timestamp.isoformat() if e.timestamp else "N/A"
                asset_ids = ", ".join(str(a) for a in (e.linked_asset_ids or []))
                evidence_lines.append(
                    f"- [{ts}] {ep.get('notes', 'No notes')} (Assets: {asset_ids})"
                )
            sections.append({
                "heading": "Evidence",
                "content": "\n".join(evidence_lines),
            })
        else:
            sections.append({
                "heading": "Evidence",
                "content": "No evidence has been linked to this case.",
            })

        # Timeline / chronological narrative
        timeline_lines = []
        for e in data["all_events"]:
            ts = e.timestamp.isoformat() if e.timestamp else "N/A"
            ep = e.payload or {}
            summary = ep.get("content") or ep.get("notes") or ep.get("title") or e.type
            timeline_lines.append(f"- [{ts}] ({e.type}) {summary}")

        timeline_summary = "\n".join(timeline_lines) if timeline_lines else "No events recorded."
        sections.append({
            "heading": "Timeline",
            "content": timeline_summary,
        })

        # Findings from notes
        note_items = data["notes"]
        if note_items:
            findings_lines = []
            for n in note_items:
                np = n.payload or {}
                findings_lines.append(f"- {np.get('content', '')}")
            sections.append({
                "heading": "Findings",
                "content": "\n".join(findings_lines),
            })

        # Evidence references
        evidence_refs = [
            {
                "id": str(e.id),
                "asset_ids": [str(a) for a in (e.linked_asset_ids or [])],
                "notes": (e.payload or {}).get("notes", ""),
            }
            for e in evidence_items
        ]

        return {
            "title": title,
            "sections": sections,
            "evidence_refs": evidence_refs,
            "timeline_summary": timeline_summary,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def export_report(
        self,
        db: AsyncSession,
        case_id: UUID,
        format: str = "markdown",
    ) -> str:
        """Export a case report in the specified format.

        Args:
            format: 'markdown' or 'json'.
        """
        report = await self.draft_report(db, case_id)

        if format == "json":
            return json.dumps(report, indent=2)

        # Default: markdown
        lines = [f"# {report['title']}", ""]
        lines.append(f"*Generated at: {report['generated_at']}*")
        lines.append("")

        for section in report["sections"]:
            lines.append(f"## {section['heading']}")
            lines.append("")
            lines.append(section["content"])
            lines.append("")

        # Evidence reference table
        if report["evidence_refs"]:
            lines.append("## Evidence References")
            lines.append("")
            lines.append("| ID | Asset IDs | Notes |")
            lines.append("|---|---|---|")
            for ref in report["evidence_refs"]:
                asset_str = ", ".join(ref["asset_ids"]) if ref["asset_ids"] else "N/A"
                lines.append(f"| {ref['id']} | {asset_str} | {ref['notes']} |")
            lines.append("")

        return "\n".join(lines)

    async def sign_report(
        self,
        db: AsyncSession,
        case_id: UUID,
        user_id: str,
    ) -> dict:
        """Sign a report: create an audit record and compute content hash."""
        # Generate the report content for hashing
        report_content = await self.export_report(db, case_id, format="markdown")
        content_hash = hashlib.sha256(report_content.encode()).hexdigest()
        signed_at = datetime.utcnow().isoformat()

        # Verify case exists (get workspace_id)
        result = await db.execute(
            select(Event).where(Event.id == case_id, Event.type == "case")
        )
        case = result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        # Store signature as an event
        signature = Event(
            id=uuid4(),
            type="report_signature",
            source="investigation",
            workspace_id=case.workspace_id,
            payload={
                "case_id": str(case_id),
                "signed_by": user_id,
                "signed_at": signed_at,
                "hash": content_hash,
            },
        )
        db.add(signature)
        await db.commit()
        await db.refresh(signature)

        return {
            "signed_by": user_id,
            "signed_at": signed_at,
            "hash": content_hash,
        }

    async def get_report_history(self, db: AsyncSession, case_id: UUID) -> list[dict]:
        """Get all report versions and signatures for a case."""
        result = await db.execute(
            select(Event)
            .where(Event.type == "report_signature")
            .order_by(Event.timestamp.asc())
        )
        all_sigs = result.scalars().all()
        case_sigs = [
            s for s in all_sigs
            if s.payload and s.payload.get("case_id") == str(case_id)
        ]

        return [
            {
                "id": str(s.id),
                "signed_by": s.payload.get("signed_by"),
                "signed_at": s.payload.get("signed_at"),
                "hash": s.payload.get("hash"),
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            }
            for s in case_sigs
        ]
