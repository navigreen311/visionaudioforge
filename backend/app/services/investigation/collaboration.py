"""Collaboration service — comments, checkpoints, approvals, reviewer assignment."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event

logger = logging.getLogger(__name__)


class CollaborationService:
    """Manages collaborative features for investigation cases."""

    async def add_comment(
        self,
        db: AsyncSession,
        case_id: UUID,
        user_id: str,
        content: str,
        parent_id: Optional[UUID] = None,
    ) -> Event:
        """Add a comment to a case. Supports threaded replies via parent_id."""
        # Verify case exists
        result = await db.execute(
            select(Event).where(Event.id == case_id, Event.type == "case")
        )
        case = result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        comment = Event(
            id=uuid4(),
            type="comment",
            source="investigation",
            workspace_id=case.workspace_id,
            payload={
                "case_id": str(case_id),
                "user_id": user_id,
                "content": content,
                "parent_id": str(parent_id) if parent_id else None,
            },
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment

    async def get_comments(self, db: AsyncSession, case_id: UUID) -> list[dict]:
        """Get all comments for a case, organized as threaded tree sorted by timestamp."""
        result = await db.execute(
            select(Event)
            .where(Event.type == "comment")
            .order_by(Event.timestamp.asc())
        )
        all_comments = result.scalars().all()
        case_comments = [
            c for c in all_comments
            if c.payload and c.payload.get("case_id") == str(case_id)
        ]

        def _serialize(c: Event) -> dict:
            return {
                "id": str(c.id),
                "user_id": c.payload.get("user_id"),
                "content": c.payload.get("content"),
                "parent_id": c.payload.get("parent_id"),
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                "replies": [],
            }

        # Build threaded structure
        comment_map: dict[str, dict] = {}
        roots: list[dict] = []

        for c in case_comments:
            serialized = _serialize(c)
            comment_map[str(c.id)] = serialized

        for c in case_comments:
            serialized = comment_map[str(c.id)]
            parent_id = c.payload.get("parent_id")
            if parent_id and parent_id in comment_map:
                comment_map[parent_id]["replies"].append(serialized)
            else:
                roots.append(serialized)

        return roots

    async def create_checkpoint(
        self,
        db: AsyncSession,
        case_id: UUID,
        user_id: str,
        title: str,
        description: str,
    ) -> Event:
        """Create a review checkpoint/milestone on a case."""
        result = await db.execute(
            select(Event).where(Event.id == case_id, Event.type == "case")
        )
        case = result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        checkpoint = Event(
            id=uuid4(),
            type="checkpoint",
            source="investigation",
            workspace_id=case.workspace_id,
            payload={
                "case_id": str(case_id),
                "user_id": user_id,
                "title": title,
                "description": description,
            },
        )
        db.add(checkpoint)
        await db.commit()
        await db.refresh(checkpoint)
        return checkpoint

    async def create_approval_request(
        self,
        db: AsyncSession,
        case_id: UUID,
        user_id: str,
        approver_id: str,
        reason: str,
    ) -> Event:
        """Create an approval request on a case."""
        result = await db.execute(
            select(Event).where(Event.id == case_id, Event.type == "case")
        )
        case = result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        approval_req = Event(
            id=uuid4(),
            type="approval_request",
            source="investigation",
            workspace_id=case.workspace_id,
            payload={
                "case_id": str(case_id),
                "requester_id": user_id,
                "approver_id": approver_id,
                "reason": reason,
                "status": "pending",
            },
        )
        db.add(approval_req)
        await db.commit()
        await db.refresh(approval_req)
        return approval_req

    async def process_approval(
        self,
        db: AsyncSession,
        approval_id: UUID,
        user_id: str,
        decision: str,
        notes: Optional[str] = None,
    ) -> Event:
        """Process an approval request: approve, reject, or request revision.

        Args:
            decision: One of 'approved', 'rejected', 'needs_revision'.
        """
        if decision not in ("approved", "rejected", "needs_revision"):
            raise ValueError(f"Invalid decision: {decision}")

        result = await db.execute(
            select(Event).where(
                Event.id == approval_id,
                Event.type == "approval_request",
            )
        )
        approval = result.scalar_one_or_none()
        if approval is None:
            raise ValueError(f"Approval request {approval_id} not found")

        # Update the approval event payload
        updated_payload = dict(approval.payload or {})
        updated_payload["status"] = decision
        updated_payload["decided_by"] = user_id
        updated_payload["decided_at"] = datetime.utcnow().isoformat()
        if notes:
            updated_payload["notes"] = notes
        approval.payload = updated_payload

        await db.commit()
        await db.refresh(approval)
        return approval

    async def get_approval_queue(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Get pending approval requests, optionally filtered by approver."""
        result = await db.execute(
            select(Event)
            .where(
                Event.workspace_id == workspace_id,
                Event.type == "approval_request",
            )
            .order_by(Event.timestamp.desc())
        )
        approvals = result.scalars().all()

        pending = []
        for a in approvals:
            payload = a.payload or {}
            if payload.get("status") != "pending":
                continue
            if user_id and payload.get("approver_id") != user_id:
                continue
            pending.append({
                "id": str(a.id),
                "case_id": payload.get("case_id"),
                "requester_id": payload.get("requester_id"),
                "approver_id": payload.get("approver_id"),
                "reason": payload.get("reason"),
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            })

        return pending

    async def get_case_approvals(
        self,
        db: AsyncSession,
        case_id: UUID,
    ) -> list[dict]:
        """Get all approval requests for a specific case."""
        result = await db.execute(
            select(Event)
            .where(Event.type == "approval_request")
            .order_by(Event.timestamp.desc())
        )
        all_approvals = result.scalars().all()
        case_approvals = [
            a for a in all_approvals
            if a.payload and a.payload.get("case_id") == str(case_id)
        ]

        items: list[dict] = []
        for a in case_approvals:
            payload = a.payload or {}
            items.append({
                "id": str(a.id),
                "case_id": payload.get("case_id"),
                "requester_id": payload.get("requester_id"),
                "approver_ids": [payload.get("approver_id", "")],
                "description": payload.get("reason", ""),
                "deadline": payload.get("deadline"),
                "status": payload.get("status", "pending"),
                "decided_by": payload.get("decided_by"),
                "decided_at": payload.get("decided_at"),
                "reject_reason": payload.get("notes"),
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            })
        return items

    async def assign_reviewer(
        self,
        db: AsyncSession,
        case_id: UUID,
        reviewer_id: str,
        due_date: Optional[datetime] = None,
    ) -> Event:
        """Assign a reviewer to a case."""
        result = await db.execute(
            select(Event).where(Event.id == case_id, Event.type == "case")
        )
        case = result.scalar_one_or_none()
        if case is None:
            raise ValueError(f"Case {case_id} not found")

        assignment = Event(
            id=uuid4(),
            type="reviewer_assignment",
            source="investigation",
            workspace_id=case.workspace_id,
            payload={
                "case_id": str(case_id),
                "reviewer_id": reviewer_id,
                "due_date": due_date.isoformat() if due_date else None,
            },
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        return assignment
