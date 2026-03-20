"""Marketplace service — browse, install, rate built-in and community plugins."""

from __future__ import annotations

import uuid
from typing import Any

from app.services.plugins.framework import PluginManager, PluginManifest


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
        # Track install counts and reviews per plugin name
        self._install_counts: dict[str, int] = {}
        self._reviews: dict[str, list[dict]] = {}

    # -- browse -------------------------------------------------------------

    async def browse_marketplace(
        self,
        category: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        results = []
        for p in self.BUILT_IN_PLUGINS:
            if category and p["category"] != category:
                continue
            if search and search.lower() not in p["name"].lower() and search.lower() not in p["description"].lower():
                continue
            results.append(
                {
                    **p,
                    "install_count": self._install_counts.get(p["name"], 0),
                    "avg_rating": self._avg_rating(p["name"]),
                }
            )
        return results

    # -- details ------------------------------------------------------------

    async def get_plugin_details(self, plugin_name: str) -> dict:
        for p in self.BUILT_IN_PLUGINS:
            if p["name"] == plugin_name:
                return {
                    **p,
                    "install_count": self._install_counts.get(plugin_name, 0),
                    "reviews": self._reviews.get(plugin_name, []),
                    "avg_rating": self._avg_rating(plugin_name),
                }
        raise ValueError(f"Plugin '{plugin_name}' not found in marketplace")

    # -- install ------------------------------------------------------------

    async def install_from_marketplace(
        self, db: Any, workspace_id: str, plugin_name: str
    ) -> dict:
        details = await self.get_plugin_details(plugin_name)
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
        self._install_counts[plugin_name] = self._install_counts.get(plugin_name, 0) + 1
        return {"installed": True}

    # -- rate ---------------------------------------------------------------

    async def rate_plugin(
        self, db: Any, plugin_id: str, user_id: str, rating: int, review: str
    ) -> dict:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        # Resolve plugin name from store
        from app.services.plugins.framework import _PLUGIN_STORE

        plugin = _PLUGIN_STORE.get(plugin_id)
        name = plugin["name"] if plugin else plugin_id
        if name not in self._reviews:
            self._reviews[name] = []
        self._reviews[name].append(
            {"user_id": user_id, "rating": rating, "review": review}
        )
        return {"rated": True}

    # -- popular ------------------------------------------------------------

    async def get_popular_plugins(self, limit: int = 10) -> list[dict]:
        plugins = await self.browse_marketplace()
        plugins.sort(key=lambda p: p.get("install_count", 0), reverse=True)
        return plugins[:limit]

    # -- helpers ------------------------------------------------------------

    def _avg_rating(self, plugin_name: str) -> float:
        reviews = self._reviews.get(plugin_name, [])
        if not reviews:
            return 0.0
        return round(sum(r["rating"] for r in reviews) / len(reviews), 1)
