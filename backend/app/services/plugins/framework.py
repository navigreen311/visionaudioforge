"""Plugin framework — registration, lifecycle, and execution engine."""

from __future__ import annotations

import importlib
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


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


# ---------------------------------------------------------------------------
# In-memory store (production would use a database table)
# ---------------------------------------------------------------------------

_PLUGIN_STORE: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# PluginManager
# ---------------------------------------------------------------------------


class PluginManager:
    """Manages plugin registration, lifecycle, configuration and execution."""

    # -- registration -------------------------------------------------------

    async def register_plugin(
        self,
        db: Any,
        workspace_id: str,
        manifest: PluginManifest,
    ) -> dict:
        """Register a new plugin from its manifest."""
        if manifest.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{manifest.category}'. "
                f"Must be one of {sorted(VALID_CATEGORIES)}"
            )

        plugin_id = str(uuid.uuid4())
        _PLUGIN_STORE[plugin_id] = {
            "plugin_id": plugin_id,
            "workspace_id": workspace_id,
            "name": manifest.name,
            "version": manifest.version,
            "author": manifest.author,
            "description": manifest.description,
            "category": manifest.category,
            "entry_point": manifest.entry_point,
            "permissions": manifest.permissions,
            "config_schema": manifest.config_schema,
            "config": {},
            "icon_url": manifest.icon_url,
            "enabled": False,
            "status": "registered",
            "install_count": 0,
            "ratings": [],
        }
        return {"plugin_id": plugin_id, "name": manifest.name, "status": "registered"}

    # -- enable / disable ---------------------------------------------------

    async def enable_plugin(self, db: Any, workspace_id: str, plugin_id: str) -> dict:
        plugin = _PLUGIN_STORE.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin {plugin_id} not found")
        plugin["enabled"] = True
        return {"enabled": True}

    async def disable_plugin(self, db: Any, workspace_id: str, plugin_id: str) -> dict:
        plugin = _PLUGIN_STORE.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin {plugin_id} not found")
        plugin["enabled"] = False
        return {"disabled": True}

    # -- listing / details --------------------------------------------------

    async def list_plugins(
        self,
        db: Any,
        workspace_id: str,
        category: str | None = None,
        enabled: bool | None = None,
    ) -> list[dict]:
        results = []
        for p in _PLUGIN_STORE.values():
            if p["workspace_id"] != workspace_id:
                continue
            if category and p["category"] != category:
                continue
            if enabled is not None and p["enabled"] != enabled:
                continue
            results.append(p)
        return results

    async def get_plugin(self, db: Any, plugin_id: str) -> dict:
        plugin = _PLUGIN_STORE.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin {plugin_id} not found")
        return plugin

    # -- configure ----------------------------------------------------------

    async def configure_plugin(self, db: Any, plugin_id: str, config: dict) -> dict:
        plugin = _PLUGIN_STORE.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin {plugin_id} not found")
        plugin["config"] = config
        return {"configured": True}

    # -- execute ------------------------------------------------------------

    async def execute_plugin(self, plugin_id: str, input_data: dict) -> dict:
        """Execute a plugin by importing its entry_point and calling it."""
        plugin = _PLUGIN_STORE.get(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin {plugin_id} not found")
        if not plugin["enabled"]:
            raise RuntimeError(f"Plugin {plugin_id} is not enabled")

        entry = plugin["entry_point"]
        start = time.perf_counter()

        try:
            # entry_point format: "module.path:function_name"
            if ":" in entry:
                mod_path, func_name = entry.rsplit(":", 1)
                mod = importlib.import_module(mod_path)
                fn = getattr(mod, func_name)
            else:
                # Fallback: treat whole string as dotted path to callable
                parts = entry.rsplit(".", 1)
                mod = importlib.import_module(parts[0])
                fn = getattr(mod, parts[1])

            # Support both sync and async callables
            import asyncio

            if asyncio.iscoroutinefunction(fn):
                result = await fn(input_data, config=plugin.get("config", {}))
            else:
                result = fn(input_data, config=plugin.get("config", {}))
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return {
                "result": {"error": str(exc)},
                "execution_time_ms": round(elapsed, 2),
            }

        elapsed = (time.perf_counter() - start) * 1000
        return {"result": result, "execution_time_ms": round(elapsed, 2)}

    # -- uninstall ----------------------------------------------------------

    async def uninstall_plugin(self, db: Any, plugin_id: str) -> dict:
        if plugin_id not in _PLUGIN_STORE:
            raise ValueError(f"Plugin {plugin_id} not found")
        del _PLUGIN_STORE[plugin_id]
        return {"removed": True}
