"""Tests for Edge Fleet Manager — device registry, OTA updates, remote config,
offline packages, bandwidth-aware sync, and device health."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from app.services.edge.fleet.device_registry import DeviceRegistry, _devices
from app.services.edge.fleet.ota_updates import OTAUpdateService, _updates
from app.services.edge.fleet.remote_config import RemoteConfigService, _configs
from app.services.edge.fleet.offline_package import OfflinePackageBuilder, _packages
from app.services.edge.fleet.sync_service import SyncService, _sync_plans
from app.services.edge.fleet.health import DeviceHealthService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
WS_ID = "test-workspace-001"
HW_INFO = {"cpu": "ARM Cortex-A57", "gpu": "NVIDIA Maxwell", "ram_mb": 4096, "storage_gb": 64}
NET_INFO = {"bandwidth_mbps": 10.0, "ip": "192.168.1.100"}


@pytest.fixture(autouse=True)
def _clear_stores():
    """Clear all in-memory stores before each test."""
    _devices.clear()
    _updates.clear()
    _configs.clear()
    _packages.clear()
    _sync_plans.clear()
    yield
    _devices.clear()
    _updates.clear()
    _configs.clear()
    _packages.clear()
    _sync_plans.clear()


# ---------------------------------------------------------------------------
# Device Registry Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_register_device():
    reg = DeviceRegistry()
    result = await reg.register_device(None, WS_ID, "cam-01", "jetson_nano", HW_INFO, NET_INFO)
    assert "device_id" in result
    assert "api_key" in result
    assert result["api_key"].startswith("vaf_dk_")
    assert "registered_at" in result


@pytest.mark.anyio
async def test_heartbeat_updates_status():
    reg = DeviceRegistry()
    dev = await reg.register_device(None, WS_ID, "cam-02", "raspberry_pi", HW_INFO)
    device_id = dev["device_id"]

    payload = {"cpu_pct": 45.0, "memory_pct": 60.0, "disk_pct": 30.0}
    ack = await reg.heartbeat(None, device_id, payload)
    assert ack["acknowledged"] is True

    details = await reg.get_device(None, device_id)
    assert details["status"] == "online"
    assert len(details["metrics_history"]) == 1
    assert details["metrics_history"][0]["cpu_pct"] == 45.0


@pytest.mark.anyio
async def test_fleet_overview():
    reg = DeviceRegistry()
    await reg.register_device(None, WS_ID, "dev-1", "jetson_nano", HW_INFO)
    dev2 = await reg.register_device(None, WS_ID, "dev-2", "raspberry_pi", HW_INFO)
    await reg.heartbeat(None, dev2["device_id"], {"cpu_pct": 50.0, "memory_pct": 70.0})

    overview = await reg.get_fleet_overview(None, WS_ID)
    assert overview["total_devices"] == 2
    assert overview["online"] == 2
    assert overview["by_type"]["jetson_nano"] == 1
    assert overview["by_type"]["raspberry_pi"] == 1


# ---------------------------------------------------------------------------
# OTA Update Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_create_ota_update():
    reg = DeviceRegistry()
    d1 = await reg.register_device(None, WS_ID, "dev-1", "jetson_nano", HW_INFO)
    d2 = await reg.register_device(None, WS_ID, "dev-2", "jetson_nano", HW_INFO)

    ota = OTAUpdateService()
    result = await ota.create_update(None, WS_ID, "model-v2", "all", "rolling")
    assert result["target_count"] == 2
    assert result["strategy"] == "rolling"

    status = await ota.get_update_status(None, result["update_id"])
    assert status["status"] == "pending_approval"
    assert status["progress"]["pending"] == 2


@pytest.mark.anyio
async def test_update_rollback():
    reg = DeviceRegistry()
    d1 = await reg.register_device(None, WS_ID, "dev-1", "jetson_nano", HW_INFO)

    ota = OTAUpdateService()
    update = await ota.create_update(None, WS_ID, "model-v3", [d1["device_id"]])
    await ota.approve_update(None, update["update_id"])

    rb = await ota.rollback_update(None, update["update_id"])
    assert rb["status"] == "rolled_back"


@pytest.mark.anyio
async def test_schedule_update():
    reg = DeviceRegistry()
    d1 = await reg.register_device(None, WS_ID, "dev-1", "jetson_nano", HW_INFO)

    ota = OTAUpdateService()
    update = await ota.create_update(None, WS_ID, "model-v4", [d1["device_id"]])
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    scheduled = await ota.schedule_update(None, update["update_id"], future)
    assert scheduled["status"] == "scheduled"
    assert scheduled["scheduled_at"] is not None


# ---------------------------------------------------------------------------
# Remote Config Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_remote_config_set_get():
    reg = DeviceRegistry()
    dev = await reg.register_device(None, WS_ID, "cfg-dev", "x86_server", HW_INFO)
    device_id = dev["device_id"]

    cfg_svc = RemoteConfigService()
    new_cfg = {"inference_settings": {"confidence_threshold": 0.8, "max_batch": 8}}
    result = await cfg_svc.set_config(None, device_id, new_cfg)
    assert result["config_version"] == 1

    current = await cfg_svc.get_config(None, device_id)
    assert current["config"]["inference_settings"]["confidence_threshold"] == 0.8


@pytest.mark.anyio
async def test_fleet_config():
    reg = DeviceRegistry()
    await reg.register_device(None, WS_ID, "f1", "jetson_nano", HW_INFO)
    await reg.register_device(None, WS_ID, "f2", "raspberry_pi", HW_INFO)

    cfg_svc = RemoteConfigService()
    fleet_cfg = {"sync_settings": {"sync_interval_s": 120, "bandwidth_limit_mbps": 5.0}}
    result = await cfg_svc.set_fleet_config(None, WS_ID, fleet_cfg)
    assert result["updated_devices"] == 2


# ---------------------------------------------------------------------------
# Offline Package Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_offline_package_build():
    builder = OfflinePackageBuilder()
    pkg = await builder.build_package(None, "model-123", "x86_server", True)
    assert "package_id" in pkg
    assert pkg["size_mb"] > 0
    assert any("model" in c["file"] for c in pkg["contents"])
    assert "instructions" in pkg


@pytest.mark.anyio
async def test_package_device_format_selection():
    builder = OfflinePackageBuilder()

    # Jetson should get TensorRT
    pkg_jetson = await builder.build_package(None, "m1", "jetson_nano")
    model_file = [c for c in pkg_jetson["contents"] if "model" in c["file"]][0]
    assert model_file["format"] == "TensorRT"

    # Raspberry Pi should get TFLite
    pkg_rpi = await builder.build_package(None, "m2", "raspberry_pi")
    model_file = [c for c in pkg_rpi["contents"] if "model" in c["file"]][0]
    assert model_file["format"] == "TFLite"

    # Browser should get WebGPU
    pkg_browser = await builder.build_package(None, "m3", "browser")
    model_file = [c for c in pkg_browser["contents"] if "model" in c["file"]][0]
    assert model_file["format"] == "WebGPU"


# ---------------------------------------------------------------------------
# Sync Service Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sync_time_estimate():
    sync = SyncService()
    est = await sync.estimate_sync_time(100.0, 10.0)
    # 100 MB / (10 Mbps / 8) = 100 / 1.25 = 80 seconds
    assert est["estimated_seconds"] == 80.0
    assert est["estimated_minutes"] == pytest.approx(1.33, abs=0.01)


@pytest.mark.anyio
async def test_delta_sync_savings():
    sync = SyncService()
    delta = await sync.delta_sync_info("model-v1", "model-v2")
    assert delta["savings_pct"] == 80.0
    assert delta["delta_size_mb"] < delta["full_size_mb"]
    assert len(delta["changed_layers"]) > 0


# ---------------------------------------------------------------------------
# Device Health Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_device_health():
    reg = DeviceRegistry()
    dev = await reg.register_device(None, WS_ID, "health-dev", "x86_server", HW_INFO)
    device_id = dev["device_id"]

    await reg.heartbeat(None, device_id, {
        "cpu_pct": 55.0, "memory_pct": 40.0, "disk_pct": 25.0,
        "gpu_pct": 30.0, "temperature_c": 62.0,
        "model_version": "v2.1", "inference_count_24h": 1500, "error_count_24h": 3,
    })

    health_svc = DeviceHealthService()
    h = await health_svc.get_device_health(None, device_id)
    assert h["cpu_pct"] == 55.0
    assert h["gpu_pct"] == 30.0
    assert h["inference_count_24h"] == 1500
    assert h["uptime_hours"] >= 0


@pytest.mark.anyio
async def test_unhealthy_detection():
    reg = DeviceRegistry()
    d1 = await reg.register_device(None, WS_ID, "ok-dev", "jetson_nano", HW_INFO)
    d2 = await reg.register_device(None, WS_ID, "bad-dev", "jetson_nano", HW_INFO)

    await reg.heartbeat(None, d1["device_id"], {"cpu_pct": 30.0, "memory_pct": 40.0, "disk_pct": 20.0})
    await reg.heartbeat(None, d2["device_id"], {"cpu_pct": 95.0, "memory_pct": 92.0, "disk_pct": 97.0})

    health_svc = DeviceHealthService()
    unhealthy = await health_svc.detect_unhealthy_devices(None, WS_ID)
    assert len(unhealthy) == 1
    assert unhealthy[0]["device_id"] == d2["device_id"]
    assert "high_cpu" in unhealthy[0]["issues"]
    assert "high_memory" in unhealthy[0]["issues"]
    assert "low_disk" in unhealthy[0]["issues"]


# ---------------------------------------------------------------------------
# API Route Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_register_device(client):
    resp = await client.post("/api/edge/devices", json={
        "workspace_id": WS_ID,
        "device_name": "api-dev-1",
        "device_type": "jetson_nano",
        "hardware_info": HW_INFO,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "device_id" in data
    assert "api_key" in data


@pytest.mark.anyio
async def test_api_update(client):
    # Register a device first
    reg_resp = await client.post("/api/edge/devices", json={
        "workspace_id": WS_ID,
        "device_name": "api-dev-2",
        "device_type": "x86_server",
        "hardware_info": HW_INFO,
    })
    device_id = reg_resp.json()["device_id"]

    # Create update
    update_resp = await client.post("/api/edge/updates", json={
        "workspace_id": WS_ID,
        "model_id": "model-v5",
        "target_devices": [device_id],
        "strategy": "immediate",
    })
    assert update_resp.status_code == 200
    update_id = update_resp.json()["update_id"]

    # Get status
    status_resp = await client.get(f"/api/edge/updates/{update_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "pending_approval"

    # Approve
    approve_resp = await client.post(f"/api/edge/updates/{update_id}/approve")
    assert approve_resp.status_code == 200


@pytest.mark.anyio
async def test_api_health(client):
    # Register and heartbeat
    reg_resp = await client.post("/api/edge/devices", json={
        "workspace_id": WS_ID,
        "device_name": "api-health-dev",
        "device_type": "raspberry_pi",
        "hardware_info": HW_INFO,
    })
    device_id = reg_resp.json()["device_id"]

    await client.post(f"/api/edge/devices/{device_id}/heartbeat", json={
        "status_payload": {"cpu_pct": 45.0, "memory_pct": 55.0, "disk_pct": 20.0},
    })

    health_resp = await client.get(f"/api/edge/devices/{device_id}/health")
    assert health_resp.status_code == 200
    data = health_resp.json()
    assert data["cpu_pct"] == 45.0

    fleet_resp = await client.get(f"/api/edge/fleet/health?workspace_id={WS_ID}")
    assert fleet_resp.status_code == 200
