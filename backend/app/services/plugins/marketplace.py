"""Marketplace service — browse, install, rate built-in and community plugins.

Install counts and reviews come out of the database rather than per-instance
dicts. Held in memory they were both lost on restart and invisible to every
other worker, so two users could see different ratings for the same plugin.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import Plugin, PluginReview
from app.services.plugins.framework import PluginManager, PluginManifest, _as_uuid


class MarketplaceService:
    """Marketplace catalog, installation, and ratings."""

    BUILT_IN_PLUGINS: list[dict[str, str]] = [
        {
            "name": "CSV Exporter",
            "category": "integration",
            "description": "Export any data as CSV",
            "version": "1.0",
            "author": "VAF Team",
            "entry_point": "app.services.plugins.builtins:csv_exporter",
        },
        {
            "name": "Slack Notifier",
            "category": "integration",
            "description": "Send alerts to Slack",
            "version": "1.0",
            "author": "VAF Team",
            "entry_point": "app.services.plugins.builtins:slack_notifier",
        },
        {
            "name": "Image Watermarker",
            "category": "transform",
            "description": "Add watermarks to images",
            "version": "1.0",
            "author": "VAF Team",
            "entry_point": "app.services.plugins.builtins:image_watermarker",
        },
        {
            "name": "Audio Normalizer",
            "category": "transform",
            "description": "Batch normalize audio files",
            "version": "1.0",
            "author": "VAF Team",
            "entry_point": "app.services.plugins.builtins:audio_normalizer",
        },
        {
            "name": "YOLO Detector",
            "category": "vision",
            "description": "Object detection with YOLOv8",
            "version": "1.0",
            "author": "VAF Team",
            "entry_point": "app.services.plugins.builtins:yolo_detector",
        },
        {
            "name": "Whisper Transcriber",
            "category": "audio",
            "description": "Speech-to-text with Whisper",
            "version": "1.0",
            "author": "VAF Team",
            "entry_point": "app.services.plugins.builtins:whisper_transcriber",
        },
        {
            "name": "Sentiment Analyzer",
            "category": "analytics",
            "description": "Text sentiment analysis",
            "version": "1.0",
            "author": "VAF Team",
            "entry_point": "app.services.plugins.builtins:sentiment_analyzer",
        },
        {
            "name": "Report Generator",
            "category": "analytics",
            "description": "Auto-generate PDF reports",
            "version": "1.0",
            "author": "VAF Team",
            "entry_point": "app.services.plugins.builtins:report_generator",
        },
    ]

    def __init__(self) -> None:
        self._plugin_manager = PluginManager()

    # -- browse -------------------------------------------------------------

    async def browse_marketplace(
        self,
        db: AsyncSession,
        category: str | None = None,
        search: str | None = None,
        workspace_id: str | None = None,
    ) -> list[dict]:
        """List catalogue entries with live install counts and ratings."""
        stats = await self._stats_by_name(db, workspace_id)

        results = []
        for plugin in self.BUILT_IN_PLUGINS:
            if category and plugin["category"] != category:
                continue
            if search:
                needle = search.lower()
                if (
                    needle not in plugin["name"].lower()
                    and needle not in plugin["description"].lower()
                ):
                    continue

            entry = stats.get(plugin["name"], {"install_count": 0, "avg_rating": 0.0})
            results.append({**plugin, **entry})
        return results

    # -- details ------------------------------------------------------------

    async def get_plugin_details(
        self,
        db: AsyncSession,
        plugin_name: str,
        workspace_id: str | None = None,
    ) -> dict:
        """Return one catalogue entry with its reviews."""
        for plugin in self.BUILT_IN_PLUGINS:
            if plugin["name"] == plugin_name:
                stats = (await self._stats_by_name(db, workspace_id)).get(
                    plugin_name, {"install_count": 0, "avg_rating": 0.0}
                )
                return {
                    **plugin,
                    **stats,
                    "reviews": await self._reviews_for(db, plugin_name, workspace_id),
                }
        raise ValueError(f"Plugin '{plugin_name}' not found in marketplace")

    # -- install ------------------------------------------------------------

    async def install_from_marketplace(
        self, db: AsyncSession, workspace_id: str, plugin_name: str
    ) -> dict:
        """Register a catalogue plugin into a workspace."""
        details = await self.get_plugin_details(db, plugin_name, workspace_id)
        manifest = PluginManifest(
            name=details["name"],
            version=details["version"],
            author=details["author"],
            description=details["description"],
            category=details["category"],
            entry_point=details["entry_point"],
            permissions=[],
            config_schema={},
            icon_url=None,
        )
        await self._plugin_manager.register_plugin(db, workspace_id, manifest)
        return {"installed": True}

    # -- rate ---------------------------------------------------------------

    async def rate_plugin(
        self,
        db: AsyncSession,
        plugin_id: str,
        user_id: str,
        rating: int,
        review: str,
    ) -> dict:
        """Attach a rating to a registered plugin."""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        plugin = await self._plugin_manager._load(db, plugin_id)
        db.add(
            PluginReview(
                id=uuid.uuid4(),
                plugin_id=plugin.id,
                rating=float(rating),
                comment=review,
                author=str(user_id) if user_id else None,
            )
        )
        await db.commit()
        return {"rated": True}

    # -- popular ------------------------------------------------------------

    async def get_popular_plugins(
        self, db: AsyncSession, limit: int = 10, workspace_id: str | None = None
    ) -> list[dict]:
        plugins = await self.browse_marketplace(db, workspace_id=workspace_id)
        plugins.sort(key=lambda p: p.get("install_count", 0), reverse=True)
        return plugins[:limit]

    # -- helpers ------------------------------------------------------------

    async def _stats_by_name(
        self, db: AsyncSession, workspace_id: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """Install count and mean rating per plugin name.

        A plugin's install count is how many registrations exist, which is a
        fact in the table rather than a counter that can drift. Scoped to a
        workspace when one is given, so one tenant's installs are not reported
        to another.
        """
        installs_q = select(Plugin.name, func.count(Plugin.id)).group_by(Plugin.name)
        if workspace_id is not None:
            installs_q = installs_q.where(Plugin.workspace_id == _as_uuid(workspace_id))
        installs = await db.execute(installs_q)
        stats: dict[str, dict[str, Any]] = {
            name: {"install_count": count, "avg_rating": 0.0}
            for name, count in installs.all()
        }

        ratings_q = (
            select(Plugin.name, func.avg(PluginReview.rating))
            .join(PluginReview, PluginReview.plugin_id == Plugin.id)
            .group_by(Plugin.name)
        )
        if workspace_id is not None:
            ratings_q = ratings_q.where(Plugin.workspace_id == _as_uuid(workspace_id))
        ratings = await db.execute(ratings_q)
        for name, average in ratings.all():
            stats.setdefault(name, {"install_count": 0})
            stats[name]["avg_rating"] = round(float(average), 1) if average else 0.0

        return stats

    async def _reviews_for(
        self,
        db: AsyncSession,
        plugin_name: str,
        workspace_id: str | None = None,
    ) -> list[dict]:
        query = (
            select(PluginReview)
            .join(Plugin, PluginReview.plugin_id == Plugin.id)
            .where(Plugin.name == plugin_name)
            .order_by(PluginReview.created_at)
        )
        if workspace_id is not None:
            query = query.where(Plugin.workspace_id == _as_uuid(workspace_id))
        result = await db.execute(query)
        return [
            {
                "user_id": review.author,
                "rating": int(review.rating),
                "review": review.comment,
            }
            for review in result.scalars().all()
        ]
