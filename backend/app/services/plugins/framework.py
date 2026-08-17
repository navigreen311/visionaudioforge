"""Plugin framework — registration, lifecycle, and execution engine.

Registrations live in the ``plugins`` table. A registration that only exists
in one worker's memory means a pipeline step resolves on one process and 404s
on the next, and disappears entirely on deploy.
"""

from __future__ import annotations

import asyncio
import importlib
import time
import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import Plugin

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {
    "vision",
    "audio",
    "transform",
    "pipeline_node",
    "integration",
    "analytics",
    "model",
}


class PluginManifest(BaseModel):
    """Manifest describing a plugin to register."""

    name: str
    version: str
    author: str
    description: str
    category: str
    entry_point: str
    permissions: list[str] = Field(default_factory=list)
    config_schema: dict = Field(default_factory=dict)
    icon_url: str | None = None


def _as_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _plugin_out(plugin: Plugin) -> dict:
    return {
        "plugin_id": str(plugin.id),
        "workspace_id": str(plugin.workspace_id) if plugin.workspace_id else None,
        "name": plugin.name,
        "version": plugin.version,
        "author": plugin.author,
        "description": plugin.description,
        "category": plugin.category,
        "entry_point": plugin.entry_point,
        "permissions": plugin.permissions or [],
        "config_schema": plugin.config_schema or {},
        "config": plugin.config or {},
        "icon_url": plugin.icon_url,
        "enabled": plugin.enabled,
        "status": plugin.status,
        "install_count": plugin.install_count,
    }


# ---------------------------------------------------------------------------
# PluginManager
# ---------------------------------------------------------------------------


class PluginManager:
    """Manages plugin registration, lifecycle, configuration and execution."""

    # -- lookup -------------------------------------------------------------

    @staticmethod
    async def _load(db: AsyncSession, plugin_id: str) -> Plugin:
        key = _as_uuid(plugin_id)
        if key is None:
            raise ValueError(f"Plugin {plugin_id} not found")

        result = await db.execute(select(Plugin).where(Plugin.id == key))
        plugin = result.scalar_one_or_none()
        if plugin is None:
            raise ValueError(f"Plugin {plugin_id} not found")
        return plugin

    # -- registration -------------------------------------------------------

    async def register_plugin(
        self,
        db: AsyncSession,
        workspace_id: str,
        manifest: PluginManifest,
    ) -> dict:
        """Register a new plugin from its manifest."""
        if manifest.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{manifest.category}'. "
                f"Must be one of {sorted(VALID_CATEGORIES)}"
            )

        plugin = Plugin(
            id=uuid.uuid4(),
            workspace_id=_as_uuid(workspace_id),
            name=manifest.name,
            version=manifest.version,
            author=manifest.author,
            description=manifest.description,
            category=manifest.category,
            entry_point=manifest.entry_point,
            permissions=manifest.permissions,
            config_schema=manifest.config_schema,
            config={},
            icon_url=manifest.icon_url,
            enabled=False,
            status="registered",
            install_count=0,
        )
        db.add(plugin)
        await db.commit()

        return {
            "plugin_id": str(plugin.id),
            "name": plugin.name,
            "status": "registered",
        }

    # -- enable / disable ---------------------------------------------------

    async def enable_plugin(
        self, db: AsyncSession, workspace_id: str, plugin_id: str
    ) -> dict:
        plugin = await self._load(db, plugin_id)
        plugin.enabled = True
        await db.commit()
        return {"enabled": True}

    async def disable_plugin(
        self, db: AsyncSession, workspace_id: str, plugin_id: str
    ) -> dict:
        plugin = await self._load(db, plugin_id)
        plugin.enabled = False
        await db.commit()
        return {"disabled": True}

    # -- listing / details --------------------------------------------------

    async def list_plugins(
        self,
        db: AsyncSession,
        workspace_id: str,
        category: str | None = None,
        enabled: bool | None = None,
    ) -> list[dict]:
        query = select(Plugin).where(Plugin.workspace_id == _as_uuid(workspace_id))
        if category:
            query = query.where(Plugin.category == category)
        if enabled is not None:
            query = query.where(Plugin.enabled == enabled)

        result = await db.execute(query.order_by(Plugin.created_at))
        return [_plugin_out(p) for p in result.scalars().all()]

    async def get_plugin(self, db: AsyncSession, plugin_id: str) -> dict:
        return _plugin_out(await self._load(db, plugin_id))

    # -- configure ----------------------------------------------------------

    async def configure_plugin(
        self, db: AsyncSession, plugin_id: str, config: dict
    ) -> dict:
        plugin = await self._load(db, plugin_id)
        plugin.config = config
        await db.commit()
        return {"configured": True}

    # -- execute ------------------------------------------------------------

    async def execute_plugin(
        self, db: AsyncSession, plugin_id: str, input_data: dict
    ) -> dict:
        """Execute a plugin by importing its entry_point and calling it."""
        plugin = await self._load(db, plugin_id)
        if not plugin.enabled:
            raise RuntimeError(f"Plugin {plugin_id} is not enabled")

        entry = plugin.entry_point
        config = plugin.config or {}
        start = time.perf_counter()

        try:
            # entry_point format: "module.path:function_name"
            if ":" in entry:
                mod_path, func_name = entry.rsplit(":", 1)
                mod = importlib.import_module(mod_path)
                fn = getattr(mod, func_name)
            else:
                # Fallback: treat whole string as dotted path to callable
                mod_path, func_name = entry.rsplit(".", 1)
                mod = importlib.import_module(mod_path)
                fn = getattr(mod, func_name)

            if asyncio.iscoroutinefunction(fn):
                result = await fn(input_data, config=config)
            else:
                result = fn(input_data, config=config)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return {
                "result": {"error": str(exc)},
                "execution_time_ms": round(elapsed, 2),
            }

        elapsed = (time.perf_counter() - start) * 1000
        return {"result": result, "execution_time_ms": round(elapsed, 2)}

    # -- uninstall ----------------------------------------------------------

    async def uninstall_plugin(self, db: AsyncSession, plugin_id: str) -> dict:
        plugin = await self._load(db, plugin_id)
        await db.delete(plugin)
        await db.commit()
        return {"removed": True}
