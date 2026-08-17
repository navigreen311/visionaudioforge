"""Tests for Edge Fleet Manager — device registry, OTA updates, remote config,
offline packages, bandwidth-aware sync, and device health.

The fleet is database-backed: these run against a real server and skip when
none is reachable (as in CI). Every test gets its own workspace, so scoping
keeps them isolated without truncating tables.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.deps import get_db
from app.main import app
from app.models.edge_fleet import DeviceStatus, EdgeDevice
from app.services.edge.fleet.device_registry import DeviceRegistry
from app.services.edge.fleet.health import DeviceHealthService
from app.services.edge.fleet.offline_package import OfflinePackageBuilder
from app.services.edge.fleet.ota_updates import OTAUpdateService
from app.services.edge.fleet.remote_config import DEFAULT_CONFIG, RemoteConfigService
from app.services.edge.fleet.sync_service import SyncService
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HW_INFO = {
    "cpu": "ARM Cortex-A57",
    "gpu": "NVIDIA Maxwell",
    "ram_mb": 4096,
    "storage_gb": 64,
}
NET_INFO = {"bandwidth_mbps": 10.0, "ip": "192.168.1.100"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def fleet():
    """Yield (session_factory, workspace_id) against a real database."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "fleet")

    try:
        yield factory, workspace_id
    finally:
        await engine.dispose()


@pytest.fixture
async def db(fleet):
    """A single session for service-level tests."""
    factory, _ = fleet
    async with factory() as session:
        yield session


@pytest.fixture
def workspace_id(fleet):
    return str(fleet[1])


@pytest.fixture
async def client(fleet):
    """HTTP client whose requests use the test database session."""
    factory, _ = fleet

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _register(db, workspace_id, name="dev-1", device_type="jetson_nano", net=None):
    registry = DeviceRegistry()
    result = await registry.register_device(
        db, workspace_id, name, device_type, HW_INFO, net or NET_INFO
    )
    return result["device_id"]


# ---------------------------------------------------------------------------
# Device Registry
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_register_device(db, workspace_id):
    """Registering returns an id and an API key."""
    registry = DeviceRegistry()
    result = await registry.register_device(
        db, workspace_id, "edge-1", "jetson_nano", HW_INFO, NET_INFO
    )

    assert result["device_id"]
    assert result["api_key"].startswith("vaf_dk_")
    assert result["registered_at"]


@pytest.mark.anyio
async def test_register_rejects_unknown_device_type(db, workspace_id):
    """An unsupported device type is refused rather than silently stored."""
    registry = DeviceRegistry()
    with pytest.raises(ValueError, match="Invalid device_type"):
        await registry.register_device(
            db, workspace_id, "edge-x", "toaster", HW_INFO, NET_INFO
        )


@pytest.mark.anyio
async def test_heartbeat_updates_status_and_records_metrics(db, workspace_id):
    """A heartbeat marks the device online and appends telemetry."""
    registry = DeviceRegistry()
    device_id = await _register(db, workspace_id)

    ack = await registry.heartbeat(
        db, device_id, {"cpu_pct": 42.0, "memory_pct": 61.0, "disk_pct": 30.0}
    )
    assert ack["acknowledged"] is True

    device = await registry.get_device(db, device_id)
    assert device["status"] == "online"
    assert device["metrics_history"][-1]["cpu_pct"] == 42.0


@pytest.mark.anyio
async def test_heartbeat_unknown_device_raises(db, workspace_id):
    """Heartbeats from unregistered devices are rejected."""
    registry = DeviceRegistry()
    with pytest.raises(KeyError):
        await registry.heartbeat(db, "not-a-device", {"cpu_pct": 1.0})


@pytest.mark.anyio
async def test_list_devices_is_workspace_scoped(fleet, db, workspace_id):
    """Devices in another workspace never appear in this workspace's list."""
    factory, _ = fleet
    registry = DeviceRegistry()

    await _register(db, workspace_id, "mine")
    async with factory() as other_session:
        other_ws = await seed_workspace(other_session, "fleet-other")
        await _register(other_session, str(other_ws), "theirs")

    devices = await registry.list_devices(db, workspace_id)
    assert [d["device_name"] for d in devices] == ["mine"]


@pytest.mark.anyio
async def test_list_devices_filters_by_status(db, workspace_id):
    """The status filter is applied in the query."""
    registry = DeviceRegistry()
    await _register(db, workspace_id, "online-dev")

    assert len(await registry.list_devices(db, workspace_id, status="online")) == 1
    assert await registry.list_devices(db, workspace_id, status="offline") == []


@pytest.mark.anyio
async def test_deregister_device(db, workspace_id):
    """Deregistering removes the device; a second attempt reports False."""
    registry = DeviceRegistry()
    device_id = await _register(db, workspace_id)

    assert await registry.deregister_device(db, device_id) is True
    assert await registry.deregister_device(db, device_id) is False
    with pytest.raises(KeyError):
        await registry.get_device(db, device_id)


@pytest.mark.anyio
async def test_fleet_overview(db, workspace_id):
    """Overview aggregates counts by type and averages latest telemetry."""
    registry = DeviceRegistry()
    d1 = await _register(db, workspace_id, "a", "jetson_nano")
    await _register(db, workspace_id, "b", "raspberry_pi")
    await registry.heartbeat(db, d1, {"cpu_pct": 50.0, "memory_pct": 60.0})

    overview = await registry.get_fleet_overview(db, workspace_id)

    assert overview["total_devices"] == 2
    assert overview["online"] == 2
    assert overview["offline"] == 0
    assert overview["by_type"] == {"jetson_nano": 1, "raspberry_pi": 1}
    assert overview["avg_cpu_pct"] == 50.0


# ---------------------------------------------------------------------------
# OTA updates
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_create_ota_update(db, workspace_id):
    """An update targets the named devices and starts awaiting approval."""
    ota = OTAUpdateService()
    device_id = await _register(db, workspace_id)

    result = await ota.create_update(db, workspace_id, "model-v2", [device_id])
    assert result["target_count"] == 1

    status = await ota.get_update_status(db, result["update_id"])
    assert status["status"] == "pending_approval"
    assert status["progress"]["pending"] == 1


@pytest.mark.anyio
async def test_create_update_targeting_all_devices(db, workspace_id):
    """'all' resolves to every device in the workspace."""
    ota = OTAUpdateService()
    await _register(db, workspace_id, "a")
    await _register(db, workspace_id, "b")

    result = await ota.create_update(db, workspace_id, "model-v2", "all")
    assert result["target_count"] == 2


@pytest.mark.anyio
async def test_create_update_rejects_bad_strategy(db, workspace_id):
    """Only the three known rollout strategies are accepted."""
    ota = OTAUpdateService()
    with pytest.raises(ValueError, match="Invalid strategy"):
        await ota.create_update(db, workspace_id, "m", "all", strategy="yolo")


@pytest.mark.anyio
async def test_approve_update_completes_rollout(db, workspace_id):
    """Approving drives every targeted device to completed."""
    ota = OTAUpdateService()
    device_id = await _register(db, workspace_id)
    update_id = (await ota.create_update(db, workspace_id, "m", [device_id]))["update_id"]

    assert (await ota.approve_update(db, update_id))["status"] == "completed"

    status = await ota.get_update_status(db, update_id)
    assert status["progress"]["completed"] == 1
    assert status["device_statuses"][0]["completed_at"] is not None


@pytest.mark.anyio
async def test_update_rollback(db, workspace_id):
    """Rollback marks the update and every device rolled back."""
    ota = OTAUpdateService()
    device_id = await _register(db, workspace_id)
    update_id = (await ota.create_update(db, workspace_id, "m", [device_id]))["update_id"]

    assert (await ota.rollback_update(db, update_id))["status"] == "rolled_back"
    status = await ota.get_update_status(db, update_id)
    assert status["device_statuses"][0]["status"] == "rolled_back"


@pytest.mark.anyio
async def test_schedule_update(db, workspace_id):
    """Scheduling records the time and flips status to scheduled."""
    ota = OTAUpdateService()
    device_id = await _register(db, workspace_id)
    update_id = (await ota.create_update(db, workspace_id, "m", [device_id]))["update_id"]

    when = datetime.now(timezone.utc) + timedelta(hours=6)
    result = await ota.schedule_update(db, update_id, when)

    assert result["status"] == "scheduled"
    assert (await ota.get_update_status(db, update_id))["status"] == "scheduled"


@pytest.mark.anyio
async def test_update_history_is_workspace_scoped(fleet, db, workspace_id):
    """Another workspace's rollouts stay out of this workspace's history."""
    factory, _ = fleet
    ota = OTAUpdateService()

    device_id = await _register(db, workspace_id)
    await ota.create_update(db, workspace_id, "mine", [device_id])

    async with factory() as other_session:
        other_ws = str(await seed_workspace(other_session, "fleet-ota-other"))
        other_device = await _register(other_session, other_ws, "theirs")
        await ota.create_update(other_session, other_ws, "theirs", [other_device])

    history = await ota.get_update_history(db, workspace_id)
    assert [u["model_id"] for u in history] == ["mine"]


@pytest.mark.anyio
async def test_unknown_update_raises(db, workspace_id):
    """An unknown update id is a KeyError, not a silent empty result."""
    ota = OTAUpdateService()
    with pytest.raises(KeyError):
        await ota.get_update_status(db, "00000000-0000-0000-0000-0000000000ff")


# ---------------------------------------------------------------------------
# Remote config
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_config_defaults_before_first_write(db, workspace_id):
    """A device with no config yet reports version 0 and the defaults."""
    config_svc = RemoteConfigService()
    device_id = await _register(db, workspace_id)

    current = await config_svc.get_config(db, device_id)
    assert current["config_version"] == 0
    assert current["config"] == DEFAULT_CONFIG


@pytest.mark.anyio
async def test_remote_config_set_get_versions(db, workspace_id):
    """Each write becomes a new version and get returns the newest."""
    config_svc = RemoteConfigService()
    device_id = await _register(db, workspace_id)

    first = await config_svc.set_config(db, device_id, {"fps": 15})
    second = await config_svc.set_config(db, device_id, {"fps": 30})

    assert (first["config_version"], second["config_version"]) == (1, 2)

    current = await config_svc.get_config(db, device_id)
    assert current["config_version"] == 2
    assert current["config"] == {"fps": 30}


@pytest.mark.anyio
async def test_config_history_and_diff(db, workspace_id):
    """History is ordered oldest-first and the diff compares the last two."""
    config_svc = RemoteConfigService()
    device_id = await _register(db, workspace_id)

    await config_svc.set_config(db, device_id, {"fps": 15, "keep": 1})
    await config_svc.set_config(db, device_id, {"fps": 30, "keep": 1})

    history = await config_svc.config_history(db, device_id)
    assert [h["config_version"] for h in history] == [1, 2]

    diff = await config_svc.get_config_diff(db, device_id)
    assert diff["has_diff"] is True
    assert diff["changes"] == [{"key": "fps", "old": 15, "new": 30}]


@pytest.mark.anyio
async def test_config_diff_needs_two_versions(db, workspace_id):
    """With a single version there is nothing to diff against."""
    config_svc = RemoteConfigService()
    device_id = await _register(db, workspace_id)
    await config_svc.set_config(db, device_id, {"fps": 15})

    assert await config_svc.get_config_diff(db, device_id) == {
        "has_diff": False,
        "changes": [],
    }


@pytest.mark.anyio
async def test_fleet_config_applies_to_every_device(db, workspace_id):
    """A fleet-wide write versions the config on all workspace devices."""
    config_svc = RemoteConfigService()
    d1 = await _register(db, workspace_id, "a")
    d2 = await _register(db, workspace_id, "b")

    result = await config_svc.set_fleet_config(db, workspace_id, {"fps": 24})
    assert result["updated_devices"] == 2

    for device_id in (d1, d2):
        assert (await config_svc.get_config(db, device_id))["config"] == {"fps": 24}


@pytest.mark.anyio
async def test_config_for_unknown_device_raises(db, workspace_id):
    """Config operations require a registered device."""
    config_svc = RemoteConfigService()
    with pytest.raises(KeyError):
        await config_svc.get_config(db, "00000000-0000-0000-0000-0000000000ff")


# ---------------------------------------------------------------------------
# Offline packages
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_offline_package_build(db, workspace_id):
    """Building returns the manifest contents and a non-zero size."""
    builder = OfflinePackageBuilder()
    result = await builder.build_package(
        db, "model-1", "jetson_nano", workspace_id=workspace_id
    )

    assert result["package_id"]
    assert result["size_mb"] > 0
    assert any(c["file"].endswith(".engine") for c in result["contents"])


@pytest.mark.anyio
@pytest.mark.parametrize(
    "device_type,expected_ext",
    [
        ("jetson_nano", ".engine"),
        ("raspberry_pi", ".tflite"),
        ("x86_server", ".onnx"),
        ("browser", ".wgsl"),
    ],
)
async def test_package_device_format_selection(db, workspace_id, device_type, expected_ext):
    """Each device type gets the model format its runtime can load."""
    builder = OfflinePackageBuilder()
    result = await builder.build_package(
        db, "model-1", device_type, workspace_id=workspace_id
    )

    model_file = next(c for c in result["contents"] if c["file"].startswith("model"))
    assert model_file["file"].endswith(expected_ext)


@pytest.mark.anyio
async def test_package_manifest_and_listing(db, workspace_id):
    """A built package can be listed and its manifest retrieved."""
    builder = OfflinePackageBuilder()
    built = await builder.build_package(
        db, "model-1", "x86_server", workspace_id=workspace_id
    )

    packages = await builder.list_packages(db, workspace_id)
    assert [p["package_id"] for p in packages] == [built["package_id"]]

    manifest = await builder.get_package_manifest(db, built["package_id"])
    assert manifest["checksum"]
    assert manifest["total_size_mb"] == built["size_mb"]


@pytest.mark.anyio
async def test_unknown_package_manifest_raises(db, workspace_id):
    builder = OfflinePackageBuilder()
    with pytest.raises(KeyError):
        await builder.get_package_manifest(db, "00000000-0000-0000-0000-0000000000ff")


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sync_time_estimate():
    """80 MB over 8 Mbps (1 MB/s) is 80 seconds."""
    result = await SyncService().estimate_sync_time(80.0, 8.0)
    assert result["estimated_seconds"] == 80.0


@pytest.mark.anyio
async def test_sync_time_rejects_zero_bandwidth():
    with pytest.raises(ValueError, match="Bandwidth must be positive"):
        await SyncService().estimate_sync_time(10.0, 0)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "bandwidth,strategy",
    [(0.5, "delta"), (3.0, "compressed"), (50.0, "full")],
)
async def test_sync_strategy_follows_bandwidth(db, workspace_id, bandwidth, strategy):
    """Narrow links get a cheaper payload instead of a longer transfer."""
    device_id = await _register(
        db, workspace_id, f"dev-{bandwidth}", net={"bandwidth_mbps": bandwidth}
    )

    plan = await SyncService().create_sync_plan(db, device_id, "model-1")
    assert plan["strategy"] == strategy
    assert plan["available_bandwidth_mbps"] == bandwidth


@pytest.mark.anyio
async def test_monitor_and_record_sync_progress(db, workspace_id):
    """Progress written by one call is readable by the next."""
    sync = SyncService()
    device_id = await _register(db, workspace_id)
    plan_id = (await sync.create_sync_plan(db, device_id, "model-1"))["plan_id"]

    assert (await sync.monitor_sync(db, plan_id))["progress_pct"] == 0.0

    await sync.record_progress(db, plan_id, 60.0)
    progress = await sync.monitor_sync(db, plan_id)

    assert progress["transferred_mb"] == 60.0
    assert progress["progress_pct"] == 50.0
    assert progress["remaining_mb"] == 60.0


@pytest.mark.anyio
async def test_delta_sync_savings():
    """The delta path reports the bandwidth it saves."""
    result = await SyncService().delta_sync_info("model-v1", "model-v2")
    assert result["savings_pct"] == 80.0


@pytest.mark.anyio
async def test_sync_plan_unknown_device_raises(db, workspace_id):
    with pytest.raises(KeyError):
        await SyncService().create_sync_plan(
            db, "00000000-0000-0000-0000-0000000000ff", "model-1"
        )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_device_health(db, workspace_id):
    """Health reads the newest heartbeat."""
    registry = DeviceRegistry()
    health = DeviceHealthService()
    device_id = await _register(db, workspace_id)

    await registry.heartbeat(
        db, device_id, {"cpu_pct": 45.0, "memory_pct": 55.0, "disk_pct": 20.0}
    )

    snapshot = await health.get_device_health(db, device_id)
    assert snapshot["cpu_pct"] == 45.0
    assert snapshot["memory_pct"] == 55.0
    assert snapshot["uptime_hours"] >= 0


@pytest.mark.anyio
async def test_fleet_health_averages(db, workspace_id):
    """Fleet health averages across devices and totals inference counts."""
    registry = DeviceRegistry()
    health = DeviceHealthService()

    d1 = await _register(db, workspace_id, "a")
    d2 = await _register(db, workspace_id, "b")
    await registry.heartbeat(db, d1, {"cpu_pct": 20.0, "inference_count_24h": 100})
    await registry.heartbeat(db, d2, {"cpu_pct": 40.0, "inference_count_24h": 50})

    fleet_health = await health.get_fleet_health(db, workspace_id)
    assert fleet_health["total_devices"] == 2
    assert fleet_health["avg_cpu_pct"] == 30.0
    assert fleet_health["total_inference_24h"] == 150


@pytest.mark.anyio
async def test_unhealthy_detection(db, workspace_id):
    """Devices over the CPU/memory/disk limits are reported with reasons."""
    registry = DeviceRegistry()
    health = DeviceHealthService()
    device_id = await _register(db, workspace_id)

    await registry.heartbeat(
        db, device_id, {"cpu_pct": 95.0, "memory_pct": 92.0, "disk_pct": 99.0}
    )

    unhealthy = await health.detect_unhealthy_devices(db, workspace_id)
    assert len(unhealthy) == 1
    assert set(unhealthy[0]["issues"]) == {"high_cpu", "high_memory", "low_disk"}


@pytest.mark.anyio
async def test_stale_device_is_marked_offline(db, workspace_id):
    """A device unseen for over an hour is flagged and marked offline."""
    health = DeviceHealthService()
    device_id = await _register(db, workspace_id)

    device = (
        await db.execute(select(EdgeDevice).where(EdgeDevice.id == device_id))
    ).scalar_one()
    device.last_seen = datetime.now(timezone.utc) - timedelta(hours=3)
    await db.commit()

    unhealthy = await health.detect_unhealthy_devices(db, workspace_id)
    assert "offline_over_1h" in unhealthy[0]["issues"]

    await db.refresh(device)
    assert device.status == DeviceStatus.offline


@pytest.mark.anyio
async def test_device_health_history_respects_window(db, workspace_id):
    """Only heartbeats inside the requested window are returned."""
    registry = DeviceRegistry()
    health = DeviceHealthService()
    device_id = await _register(db, workspace_id)

    await registry.heartbeat(db, device_id, {"cpu_pct": 10.0})
    history = await health.device_health_history(db, device_id, hours=24)

    assert len(history) == 1
    assert history[0]["cpu_pct"] == 10.0


# ---------------------------------------------------------------------------
# Durability — the point of moving this off module-level dicts
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_fleet_state_survives_a_restart(fleet):
    """Write through one engine, read through a brand-new one.

    A fresh engine means a fresh connection pool and a fresh session identity
    map — nothing carries over in process memory, so anything still readable
    genuinely came back out of Postgres.
    """
    factory, workspace = fleet
    workspace_id = str(workspace)

    registry = DeviceRegistry()
    ota = OTAUpdateService()
    config_svc = RemoteConfigService()
    builder = OfflinePackageBuilder()
    sync = SyncService()

    async with factory() as session:
        device_id = await _register(session, workspace_id, "durable-device")
        await registry.heartbeat(session, device_id, {"cpu_pct": 33.0})
        update_id = (
            await ota.create_update(session, workspace_id, "model-v9", [device_id])
        )["update_id"]
        await config_svc.set_config(session, device_id, {"fps": 12})
        package_id = (
            await builder.build_package(
                session, "model-v9", "jetson_nano", workspace_id=workspace_id
            )
        )["package_id"]
        plan_id = (await sync.create_sync_plan(session, device_id, "model-v9"))["plan_id"]

    # Simulate the process going away and coming back.
    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)

    try:
        async with restarted() as session:
            device = await registry.get_device(session, device_id)
            assert device["device_name"] == "durable-device"
            assert device["metrics_history"][-1]["cpu_pct"] == 33.0

            devices = await registry.list_devices(session, workspace_id)
            assert [d["device_id"] for d in devices] == [device_id]

            status = await ota.get_update_status(session, update_id)
            assert status["progress"]["total"] == 1

            config = await config_svc.get_config(session, device_id)
            assert config["config"] == {"fps": 12}
            assert config["config_version"] == 1

            manifest = await builder.get_package_manifest(session, package_id)
            assert manifest["checksum"]

            progress = await sync.monitor_sync(session, plan_id)
            assert progress["speed_mbps"] > 0
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_two_sessions_see_each_others_writes(fleet):
    """Two concurrent sessions share state — the app can run >1 worker."""
    factory, workspace = fleet
    workspace_id = str(workspace)
    registry = DeviceRegistry()

    async with factory() as writer:
        device_id = await _register(writer, workspace_id, "shared")

    async with factory() as reader:
        devices = await registry.list_devices(reader, workspace_id)

    assert [d["device_id"] for d in devices] == [device_id]


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_register_and_get_device(client, workspace_id):
    """POST /api/fleet/devices persists through the same tables."""
    resp = await client.post(
        f"/api/fleet/devices?workspace_id={workspace_id}",
        json={"name": "api-dev-1", "device_type": "jetson_nano", "capabilities": HW_INFO},
    )
    assert resp.status_code == 201
    device_id = resp.json()["device_id"]
    assert resp.json()["api_key"].startswith("vaf_dk_")

    detail = await client.get(f"/api/fleet/devices/{device_id}")
    assert detail.status_code == 200
    assert detail.json()["device_name"] == "api-dev-1"


@pytest.mark.anyio
async def test_api_register_rejects_bad_device_type(client, workspace_id):
    resp = await client.post(
        f"/api/fleet/devices?workspace_id={workspace_id}",
        json={"name": "bad", "device_type": "toaster"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_api_list_devices_is_scoped(client, workspace_id):
    await client.post(
        f"/api/fleet/devices?workspace_id={workspace_id}",
        json={"name": "listed", "device_type": "x86_server"},
    )

    resp = await client.get(f"/api/fleet/devices?workspace_id={workspace_id}")
    assert resp.status_code == 200
    assert [d["device_name"] for d in resp.json()] == ["listed"]


@pytest.mark.anyio
async def test_api_heartbeat_and_health(client, workspace_id):
    """A heartbeat posted over HTTP shows up in the fleet health summary."""
    reg = await client.post(
        f"/api/fleet/devices?workspace_id={workspace_id}",
        json={"name": "api-health-dev", "device_type": "raspberry_pi"},
    )
    device_id = reg.json()["device_id"]

    hb = await client.post(
        f"/api/fleet/devices/{device_id}/heartbeat",
        json={"cpu_percent": 45.0, "memory_percent": 55.0, "inference_count": 7},
    )
    assert hb.status_code == 200

    health = await client.get(f"/api/fleet/health?workspace_id={workspace_id}")
    assert health.status_code == 200
    body = health.json()
    assert body["total_devices"] == 1
    assert body["online"] == 1
    assert body["avg_cpu_pct"] == 45.0
    assert body["total_inference_24h"] == 7


@pytest.mark.anyio
async def test_api_heartbeat_unknown_device_404s(client):
    resp = await client.post(
        "/api/fleet/devices/00000000-0000-0000-0000-0000000000ff/heartbeat",
        json={"cpu_percent": 1.0},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_api_deregister_device(client, workspace_id):
    reg = await client.post(
        f"/api/fleet/devices?workspace_id={workspace_id}",
        json={"name": "doomed", "device_type": "mobile"},
    )
    device_id = reg.json()["device_id"]

    assert (await client.delete(f"/api/fleet/devices/{device_id}")).status_code == 204
    assert (await client.get(f"/api/fleet/devices/{device_id}")).status_code == 404
