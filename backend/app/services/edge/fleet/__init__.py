"""Edge Fleet Manager — device registration, OTA updates, remote config,
offline packages, and bandwidth-aware sync."""

from app.services.edge.fleet.device_registry import DeviceRegistry
from app.services.edge.fleet.ota_updates import OTAUpdateService
from app.services.edge.fleet.remote_config import RemoteConfigService
from app.services.edge.fleet.offline_package import OfflinePackageBuilder
from app.services.edge.fleet.sync_service import SyncService
from app.services.edge.fleet.health import DeviceHealthService

__all__ = [
    "DeviceRegistry",
    "OTAUpdateService",
    "RemoteConfigService",
    "OfflinePackageBuilder",
    "SyncService",
    "DeviceHealthService",
]
