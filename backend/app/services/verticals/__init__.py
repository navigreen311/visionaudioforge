"""Vertical starter packs — pre-configured pipelines, alerts, and dashboards for industry verticals."""

from app.services.verticals.security import SecurityVerticalPack

VERTICAL_PACKS = {
    "security": SecurityVerticalPack,
}

__all__ = ["VERTICAL_PACKS", "SecurityVerticalPack"]
