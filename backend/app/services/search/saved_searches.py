"""Saved search service — persist, list, execute, and schedule saved searches."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SavedSearchService:
    """CRUD and execution for saved searches stored as Event records."""

    async def save_search(
        self,
        db: Any,
        workspace_id: str,
        user_id: str,
        name: str,
        query: str,
        modality: str,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist a saved search as an Event with type='saved_search'.

        Returns:
            Dict representation of the created event.
        """
        search_id = str(uuid.uuid4())
        payload = {
            "search_id": search_id,
            "user_id": user_id,
            "name": name,
            "query": query,
            "modality": modality,
            "filters": filters or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            from app.models.event import Event as EventModel

            event = EventModel(
                type="saved_search",
                payload=payload,
                source="saved_search_service",
                workspace_id=uuid.UUID(workspace_id),
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)
            return {
                "id": str(event.id),
                "type": event.type,
                "payload": event.payload,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "workspace_id": workspace_id,
            }
        except Exception:
            logger.exception("Failed to save search to DB — returning in-memory record")
            return {
                "id": search_id,
                "type": "saved_search",
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "workspace_id": workspace_id,
            }

    async def list_saved_searches(
        self,
        db: Any,
        workspace_id: str,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List saved searches for a workspace, optionally filtered by user.

        Returns:
            List of saved search dicts.
        """
        try:
            from sqlalchemy import select
            from app.models.event import Event as EventModel

            stmt = (
                select(EventModel)
                .where(EventModel.workspace_id == uuid.UUID(workspace_id))
                .where(EventModel.type == "saved_search")
                .order_by(EventModel.timestamp.desc())
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()

            searches = []
            for row in rows:
                payload = row.payload or {}
                if user_id and payload.get("user_id") != user_id:
                    continue
                searches.append({
                    "id": str(row.id),
                    "type": row.type,
                    "payload": payload,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                    "workspace_id": str(row.workspace_id),
                })
            return searches
        except Exception:
            logger.exception("Failed to list saved searches")
            return []

    async def execute_saved_search(
        self,
        db: Any,
        search_id: str,
    ) -> list[dict[str, Any]]:
        """Re-run a saved search by its event ID.

        Returns:
            Search results from re-executing the saved query.
        """
        try:
            from sqlalchemy import select
            from app.models.event import Event as EventModel

            stmt = select(EventModel).where(EventModel.id == uuid.UUID(search_id))
            result = await db.execute(stmt)
            event = result.scalar_one_or_none()

            if event is None or event.type != "saved_search":
                logger.warning("Saved search %s not found", search_id)
                return []

            payload = event.payload or {}
            query = payload.get("query", "")
            modality = payload.get("modality", "text")

            # Import and use the search service
            from app.services.search.embeddings import EmbeddingService
            from app.services.search.faiss_index import FAISSIndexService
            from app.services.search.search_service import CrossModalSearchService

            embedding_svc = EmbeddingService()
            index_svc = FAISSIndexService(dimension=512)
            index_svc.create_index("flat")
            search_svc = CrossModalSearchService(
                embedding_svc=embedding_svc,
                index_svc=index_svc,
                db_session=db,
            )
            results = await search_svc.search_by_text(query=query, k=10, modality_filter=modality if modality != "text" else None)
            return results
        except Exception:
            logger.exception("Failed to execute saved search %s", search_id)
            return []

    async def delete_saved_search(
        self,
        db: Any,
        search_id: str,
    ) -> bool:
        """Delete a saved search by its event ID.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            from sqlalchemy import select, delete
            from app.models.event import Event as EventModel

            stmt = select(EventModel).where(
                EventModel.id == uuid.UUID(search_id),
                EventModel.type == "saved_search",
            )
            result = await db.execute(stmt)
            event = result.scalar_one_or_none()
            if event is None:
                return False

            await db.delete(event)
            await db.commit()
            return True
        except Exception:
            logger.exception("Failed to delete saved search %s", search_id)
            return False

    async def create_search_alert(
        self,
        db: Any,
        search_id: str,
        frequency: str = "daily",
    ) -> dict[str, Any]:
        """Schedule periodic re-execution of a saved search.

        Returns:
            Alert schedule dict.
        """
        alert_id = str(uuid.uuid4())
        schedule = {
            "alert_id": alert_id,
            "search_id": search_id,
            "frequency": frequency,
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "next_run": datetime.now(timezone.utc).isoformat(),
        }

        try:
            from app.models.event import Event as EventModel

            # Look up the saved search to get workspace_id
            from sqlalchemy import select
            stmt = select(EventModel).where(EventModel.id == uuid.UUID(search_id))
            result = await db.execute(stmt)
            event = result.scalar_one_or_none()

            workspace_id = event.workspace_id if event else uuid.UUID("00000000-0000-0000-0000-000000000000")

            alert_event = EventModel(
                type="search_alert_schedule",
                payload=schedule,
                source="saved_search_service",
                workspace_id=workspace_id,
            )
            db.add(alert_event)
            await db.commit()
            await db.refresh(alert_event)
            schedule["id"] = str(alert_event.id)
        except Exception:
            logger.exception("Failed to persist search alert — returning in-memory schedule")
            schedule["id"] = alert_id

        return schedule
