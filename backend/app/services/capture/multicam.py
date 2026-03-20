"""Multi-camera source manager."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


class MultiCamManager:
    """Manage multiple capture sources per workspace with switching."""

    VALID_TYPES = {"webcam", "screen", "rtsp", "file"}

    def __init__(self) -> None:
        # workspace_id -> list of source dicts
        self._sources: dict[str, list[dict]] = {}
        # workspace_id -> active source_id
        self._active: dict[str, str] = {}

    async def add_source(
        self, workspace_id: str, source_type: str, config: dict | None = None
    ) -> str:
        """Register a new capture source. Returns source_id."""
        if source_type not in self.VALID_TYPES:
            raise ValueError(
                f"Invalid source_type '{source_type}'. Must be one of {self.VALID_TYPES}"
            )

        source_id = str(uuid.uuid4())
        source = {
            "source_id": source_id,
            "workspace_id": workspace_id,
            "source_type": source_type,
            "config": config or {},
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        self._sources.setdefault(workspace_id, []).append(source)

        # Auto-set as active if it's the first source
        if workspace_id not in self._active:
            self._active[workspace_id] = source_id

        return source_id

    async def remove_source(self, source_id: str) -> bool:
        """Remove a source by ID. Returns True if found and removed."""
        for wid, sources in self._sources.items():
            for s in sources:
                if s["source_id"] == source_id:
                    sources.remove(s)
                    # Clear active if it was the removed source
                    if self._active.get(wid) == source_id:
                        self._active[wid] = (
                            sources[0]["source_id"] if sources else ""
                        )
                    return True
        return False

    async def list_sources(self, workspace_id: str) -> list[dict]:
        """Return all sources for a workspace with status."""
        sources = self._sources.get(workspace_id, [])
        active_id = self._active.get(workspace_id)
        return [
            {**s, "is_primary": s["source_id"] == active_id}
            for s in sources
        ]

    async def get_active_source(self, workspace_id: str) -> dict | None:
        """Return the current primary source for a workspace."""
        active_id = self._active.get(workspace_id)
        if not active_id:
            return None
        for s in self._sources.get(workspace_id, []):
            if s["source_id"] == active_id:
                return {**s, "is_primary": True}
        return None

    async def switch_source(self, workspace_id: str, source_id: str) -> bool:
        """Set a source as the primary for a workspace."""
        sources = self._sources.get(workspace_id, [])
        for s in sources:
            if s["source_id"] == source_id:
                self._active[workspace_id] = source_id
                return True
        return False

    async def get_grid_layout(self, workspace_id: str) -> dict:
        """Determine the optimal grid layout based on source count."""
        sources = self._sources.get(workspace_id, [])
        count = len(sources)

        if count <= 1:
            layout = "1x1"
            cols, rows = 1, 1
        elif count <= 4:
            layout = "2x2"
            cols, rows = 2, 2
        elif count <= 9:
            layout = "3x3"
            cols, rows = 3, 3
        else:
            layout = "4x4"
            cols, rows = 4, 4

        return {
            "layout": layout,
            "cols": cols,
            "rows": rows,
            "source_count": count,
            "source_ids": [s["source_id"] for s in sources],
        }


# Singleton instance
multicam_manager = MultiCamManager()
