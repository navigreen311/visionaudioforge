"""StreamManager — multi-stream lifecycle, layout, and health monitoring."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.command_center import (
    CommandLayout,
    CommandStream,
    StreamSourceType,
    StreamStatus,
)

logger = logging.getLogger(__name__)

# Valid layout presets
VALID_LAYOUTS = {"2x2", "3x3", "4x4", "1+3", "1+5"}


class StreamManager:
    """Manages multi-stream views for a Command Center workspace."""

    # ------------------------------------------------------------------
    # Stream CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def add_stream(
        db: AsyncSession,
        workspace_id: str,
        name: str,
        source_type: str,
        source_config: dict[str, Any],
        position: Optional[int] = None,
    ) -> dict[str, Any]:
        """Add a new stream to the workspace layout."""
        wid = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id

        # Determine next position if not provided
        if position is None:
            result = await db.execute(
                select(func.coalesce(func.max(CommandStream.position), -1))
                .where(CommandStream.workspace_id == wid)
            )
            position = result.scalar() + 1

        stream = CommandStream(
            workspace_id=wid,
            name=name,
            source_type=StreamSourceType(source_type),
            source_config=source_config,
            position=position,
            status=StreamStatus.connected,
        )
        db.add(stream)
        await db.commit()
        await db.refresh(stream)

        logger.info("Stream %s added to workspace %s at position %d", stream.id, workspace_id, position)
        return {
            "stream_id": str(stream.id),
            "name": stream.name,
            "source_type": stream.source_type.value,
            "position": stream.position,
            "status": stream.status.value,
        }

    @staticmethod
    async def remove_stream(
        db: AsyncSession,
        workspace_id: str,
        stream_id: str,
    ) -> bool:
        """Remove a stream from the workspace."""
        wid = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id
        sid = uuid.UUID(stream_id) if isinstance(stream_id, str) else stream_id

        result = await db.execute(
            select(CommandStream)
            .where(CommandStream.workspace_id == wid, CommandStream.id == sid)
        )
        stream = result.scalar_one_or_none()
        if stream is None:
            return False

        await db.delete(stream)
        await db.commit()
        logger.info("Stream %s removed from workspace %s", stream_id, workspace_id)
        return True

    @staticmethod
    async def list_streams(
        db: AsyncSession,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        """List all active streams in a workspace."""
        wid = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id

        result = await db.execute(
            select(CommandStream)
            .where(CommandStream.workspace_id == wid)
            .order_by(CommandStream.position)
        )
        streams = result.scalars().all()
        return [
            {
                "stream_id": str(s.id),
                "name": s.name,
                "source_type": s.source_type.value,
                "position": s.position,
                "status": s.status.value,
            }
            for s in streams
        ]

    # ------------------------------------------------------------------
    # Layout management
    # ------------------------------------------------------------------

    @staticmethod
    async def get_layout(
        db: AsyncSession,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Get the current layout configuration for a workspace."""
        wid = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id

        result = await db.execute(
            select(CommandLayout).where(CommandLayout.workspace_id == wid)
        )
        layout_row = result.scalar_one_or_none()
        layout_name = layout_row.layout if layout_row else "2x2"

        streams = await StreamManager.list_streams(db, workspace_id)
        return {"layout": layout_name, "streams": streams}

    @staticmethod
    async def set_layout(
        db: AsyncSession,
        workspace_id: str,
        layout: str,
    ) -> dict[str, Any]:
        """Set the layout preset for a workspace."""
        if layout not in VALID_LAYOUTS:
            raise ValueError(f"Invalid layout '{layout}'. Must be one of {VALID_LAYOUTS}")

        wid = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id

        result = await db.execute(
            select(CommandLayout).where(CommandLayout.workspace_id == wid)
        )
        layout_row = result.scalar_one_or_none()

        if layout_row:
            layout_row.layout = layout
        else:
            layout_row = CommandLayout(workspace_id=wid, layout=layout)
            db.add(layout_row)

        await db.commit()
        return await StreamManager.get_layout(db, workspace_id)

    @staticmethod
    async def reorder_streams(
        db: AsyncSession,
        workspace_id: str,
        stream_positions: dict[str, int],
    ) -> list[dict[str, Any]]:
        """Reorder streams by setting new positions."""
        wid = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id

        for sid_str, pos in stream_positions.items():
            sid = uuid.UUID(sid_str)
            await db.execute(
                update(CommandStream)
                .where(CommandStream.workspace_id == wid, CommandStream.id == sid)
                .values(position=pos)
            )
        await db.commit()
        return await StreamManager.list_streams(db, workspace_id)

    # ------------------------------------------------------------------
    # Health monitoring
    # ------------------------------------------------------------------

    @staticmethod
    async def get_stream_health(
        db: AsyncSession,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        """Return health metrics for all streams in the workspace."""
        wid = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id

        result = await db.execute(
            select(CommandStream).where(CommandStream.workspace_id == wid)
        )
        streams = result.scalars().all()
        return [
            {
                "stream_id": str(s.id),
                "status": s.status.value,
                "fps": s.fps or 0.0,
                "latency_ms": s.latency_ms or 0.0,
                "last_frame": s.last_frame_at.isoformat() if s.last_frame_at else None,
            }
            for s in streams
        ]
