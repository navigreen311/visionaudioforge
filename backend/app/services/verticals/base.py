"""Base class for vertical starter packs."""

from __future__ import annotations

from typing import Any


class VerticalPack:
    """Abstract base for all vertical starter packs.

    Each pack defines:
    - ``info()``: metadata (name, slug, icon, description, category)
    - ``pipelines()``: pre-built pipeline definitions with nodes/edges
    - ``alert_presets()``: alert rule presets with conditions
    - ``dashboard_widgets()``: dashboard widget configurations
    - ``reports()``: report template definitions
    """

    def info(self) -> dict[str, Any]:
        """Return pack metadata."""
        raise NotImplementedError

    def pipelines(self) -> dict[str, dict[str, Any]]:
        """Return pipeline definitions keyed by slug."""
        raise NotImplementedError

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        """Return alert preset definitions keyed by slug."""
        raise NotImplementedError

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        """Return dashboard widget configurations."""
        return []

    def reports(self) -> dict[str, dict[str, Any]]:
        """Return report template definitions keyed by slug."""
        return {}
