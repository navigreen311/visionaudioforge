"""Vertical starter packs for industry-specific deployments.

``VERTICAL_PACKS`` is the canonical slug -> pack-class registry. It lives here
so callers can discover packs without importing the installer's internals.
"""

from app.services.verticals.base import VerticalPack
from app.services.verticals.callcenter import CallCenterVerticalPack
from app.services.verticals.education import EducationVerticalPack
from app.services.verticals.healthcare import HealthcareVerticalPack
from app.services.verticals.industrial import IndustrialVerticalPack
from app.services.verticals.media import MediaVerticalPack
from app.services.verticals.retail import RetailVerticalPack
from app.services.verticals.security import SecurityVerticalPack

VERTICAL_PACKS: dict[str, type[VerticalPack]] = {
    "security": SecurityVerticalPack,
    "healthcare": HealthcareVerticalPack,
    "callcenter": CallCenterVerticalPack,
    "retail": RetailVerticalPack,
    "industrial": IndustrialVerticalPack,
    "media": MediaVerticalPack,
    "education": EducationVerticalPack,
}

__all__ = [
    "VERTICAL_PACKS",
    "VerticalPack",
    "CallCenterVerticalPack",
    "EducationVerticalPack",
    "HealthcareVerticalPack",
    "IndustrialVerticalPack",
    "MediaVerticalPack",
    "RetailVerticalPack",
    "SecurityVerticalPack",
]
