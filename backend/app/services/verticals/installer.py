"""Vertical pack installer — registry, install, and uninstall logic."""

from __future__ import annotations

import logging
from typing import Any

from app.services.verticals.base import VerticalPack
from app.services.verticals.callcenter import CallCenterVerticalPack
from app.services.verticals.education import EducationVerticalPack
from app.services.verticals.healthcare import HealthcareVerticalPack
from app.services.verticals.industrial import IndustrialVerticalPack
from app.services.verticals.media import MediaVerticalPack
from app.services.verticals.retail import RetailVerticalPack
from app.services.verticals.security import SecurityVerticalPack

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pack registry — every available vertical pack
# ---------------------------------------------------------------------------

AVAILABLE_PACKS: dict[str, type[VerticalPack]] = {
    "security": SecurityVerticalPack,
    "healthcare": HealthcareVerticalPack,
    "callcenter": CallCenterVerticalPack,
    "retail": RetailVerticalPack,
    "industrial": IndustrialVerticalPack,
    "media": MediaVerticalPack,
    "education": EducationVerticalPack,
}

# In-memory store of installed packs (slug → instance).
# In a real deployment this would be backed by a database.
_installed_packs: dict[str, VerticalPack] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_available_packs() -> list[dict[str, Any]]:
    """Return metadata for every available vertical pack."""
    result: list[dict[str, Any]] = []
    for slug, cls in AVAILABLE_PACKS.items():
        pack = cls()
        info = pack.info()
        info["installed"] = slug in _installed_packs
        result.append(info)
    return result


def get_pack(slug: str) -> VerticalPack | None:
    """Return a pack instance by slug, or ``None``."""
    cls = AVAILABLE_PACKS.get(slug)
    return cls() if cls else None


def install_pack(slug: str) -> dict[str, Any]:
    """Install a vertical pack and return summary of what was provisioned.

    Returns::

        {
            "slug": str,
            "pipelines_installed": int,
            "alert_presets_installed": int,
            "dashboard_widgets": int,
            "reports_installed": int,
        }
    """
    cls = AVAILABLE_PACKS.get(slug)
    if cls is None:
        raise KeyError(f"Unknown vertical pack: {slug}")

    pack = cls()
    _installed_packs[slug] = pack

    pipelines = pack.pipelines()
    presets = pack.alert_presets()
    widgets = pack.dashboard_widgets()
    reports = pack.reports()

    logger.info(
        "Installed vertical pack '%s': %d pipelines, %d alert presets, %d widgets, %d reports",
        slug,
        len(pipelines),
        len(presets),
        len(widgets),
        len(reports),
    )

    return {
        "slug": slug,
        "pipelines_installed": len(pipelines),
        "alert_presets_installed": len(presets),
        "dashboard_widgets": len(widgets),
        "reports_installed": len(reports),
    }


def uninstall_pack(slug: str) -> bool:
    """Remove an installed pack. Returns ``True`` if it was installed."""
    removed = _installed_packs.pop(slug, None)
    if removed:
        logger.info("Uninstalled vertical pack '%s'", slug)
    return removed is not None


def is_installed(slug: str) -> bool:
    """Check whether a pack is currently installed."""
    return slug in _installed_packs


def get_installed_packs() -> dict[str, VerticalPack]:
    """Return all currently installed packs."""
    return dict(_installed_packs)


def reset() -> None:
    """Clear all installed packs (useful for testing)."""
    _installed_packs.clear()
