"""Comprehensive V3 end-to-end integration tests for VisionAudioForge v1.0.

Tests exercise all Phase 4 modules through the HTTP API, verifying that
routes are registered, respond without 404s, and return expected data shapes.
"""

import uuid

import pytest

from app.core.deps import get_db
from app.main import app
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    postgres_available,
    requires_postgres,
    seed_workspace,
)

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.fixture(autouse=True)
async def _database():
    """Point database-backed routes at the test database when one is reachable.

    Several of these flows (fleet, plugins) now read and write real tables, so
    without this they would hit the configured production host. Tests that
    cannot work at all without a database call `requires_postgres()` and skip;
    the rest are unaffected either way.
    """
    if not await postgres_available():
        yield None
        return

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "v3-e2e")

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    try:
        yield str(workspace_id)
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()

OK = (200, 201)
ACCEPTABLE = (200, 201, 400, 422, 501)
NOT_404 = lambda r: r.status_code != 404  # noqa: E731


# ---------------------------------------------------------------------------
# Knowledge Graph flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_knowledge_graph_flow(test_app):
    """add node -> add edge -> get neighbors -> scene extract."""
    # Add nodes
    r1 = await test_app.post(
        "/api/knowledge-graph/nodes",
        json={"label": "Camera-01", "node_type": "device", "properties": {"zone": "north"}},
    )
    assert r1.status_code != 404, "knowledge-graph/nodes POST returned 404"
    node1_id = r1.json().get("id", "n1") if r1.status_code in OK else "n1"

    r2 = await test_app.post(
        "/api/knowledge-graph/nodes",
        json={"label": "Zone-North", "node_type": "zone"},
    )
    assert r2.status_code != 404
    node2_id = r2.json().get("id", "n2") if r2.status_code in OK else "n2"

    # Add edge
    r3 = await test_app.post(
        "/api/knowledge-graph/edges",
        json={"source_id": node1_id, "target_id": node2_id, "relation": "located_in"},
    )
    assert r3.status_code != 404, "knowledge-graph/edges POST returned 404"

    # Get neighbors
    r4 = await test_app.get(f"/api/knowledge-graph/nodes/{node1_id}/neighbors")
    assert r4.status_code != 404, "knowledge-graph neighbors returned 404"
    if r4.status_code in OK:
        data = r4.json()
        assert "neighbors" in data

    # Scene extract
    r5 = await test_app.post(
        "/api/knowledge-graph/scene-extract",
        json={"description": "Camera watching Parking lot near Building entrance"},
    )
    assert r5.status_code != 404, "knowledge-graph/scene-extract returned 404"
    if r5.status_code in OK:
        assert "entities_extracted" in r5.json()


# ---------------------------------------------------------------------------
# Semantic Memory flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_memory_flow(test_app):
    """store -> recall -> decay -> promote."""
    # Store
    r1 = await test_app.post(
        "/api/semantic-memory/store",
        json={"content": "The north camera detected motion at 2am", "category": "alert", "importance": 0.8},
    )
    assert r1.status_code != 404, "semantic-memory/store returned 404"
    mem_id = r1.json().get("id", "m1") if r1.status_code in OK else "m1"

    # Recall
    r2 = await test_app.post(
        "/api/semantic-memory/recall",
        json={"query": "motion", "limit": 5},
    )
    assert r2.status_code != 404, "semantic-memory/recall returned 404"
    if r2.status_code in OK:
        assert "results" in r2.json()

    # Decay
    r3 = await test_app.post("/api/semantic-memory/decay?threshold=0.1&factor=0.95")
    assert r3.status_code != 404, "semantic-memory/decay returned 404"

    # Promote
    r4 = await test_app.post(f"/api/semantic-memory/promote/{mem_id}?boost=0.1")
    assert r4.status_code != 404, "semantic-memory/promote returned 404"


# ---------------------------------------------------------------------------
# Command Center flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_command_center_flow(test_app):
    """add stream -> set layout -> create shift -> get dashboard."""
    # Add stream
    r1 = await test_app.post(
        "/api/command-center/streams",
        json={"name": "Lobby Camera", "source_url": "rtsp://192.168.1.100/stream1"},
    )
    assert r1.status_code != 404, "command-center/streams POST returned 404"

    # Set layout
    r2 = await test_app.post(
        "/api/command-center/layout",
        json={"name": "quad-view", "columns": 2, "rows": 2, "grid": [["s1", "s2"], ["s3", "s4"]]},
    )
    assert r2.status_code != 404, "command-center/layout POST returned 404"

    # Create shift
    r3 = await test_app.post(
        "/api/command-center/shifts",
        json={"operator_id": "op-001", "start_time": "2026-03-20T08:00:00", "end_time": "2026-03-20T16:00:00"},
    )
    assert r3.status_code != 404, "command-center/shifts POST returned 404"

    # Dashboard
    r4 = await test_app.get("/api/command-center/dashboard")
    assert r4.status_code != 404, "command-center/dashboard returned 404"
    if r4.status_code in OK:
        data = r4.json()
        assert "total_streams" in data
        assert "status" in data


# ---------------------------------------------------------------------------
# Simulation flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_simulation_flow(test_app):
    """generate scenario -> run simulation -> get report."""
    # Generate scenario
    r1 = await test_app.post(
        "/api/simulation/scenarios",
        json={"name": "peak-load-test", "scenario_type": "stress-test", "parameters": {"concurrent_users": 500}},
    )
    assert r1.status_code != 404, "simulation/scenarios POST returned 404"
    scenario_id = r1.json().get("id", "s1") if r1.status_code in OK else "s1"

    # Run simulation
    r2 = await test_app.post(
        "/api/simulation/run",
        json={"scenario_id": scenario_id, "config": {"duration_seconds": 60}},
    )
    assert r2.status_code != 404, "simulation/run returned 404"
    sim_id = r2.json().get("id", "sim1") if r2.status_code in OK else "sim1"

    # Get report
    r3 = await test_app.get(f"/api/simulation/report/{sim_id}")
    assert r3.status_code != 404, "simulation/report returned 404"
    if r3.status_code in OK:
        assert "results" in r3.json()


# ---------------------------------------------------------------------------
# ReviewOps flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reviewops_flow(test_app):
    """create task -> assign -> submit review -> check complete."""
    # Create task
    r1 = await test_app.post(
        "/api/reviewops/tasks",
        json={"title": "Review batch-42 annotations", "description": "Check labeling quality"},
    )
    assert r1.status_code != 404, "reviewops/tasks POST returned 404"
    task_id = r1.json().get("id", "t1") if r1.status_code in OK else "t1"

    # Assign
    r2 = await test_app.post(
        f"/api/reviewops/tasks/{task_id}/assign",
        json={"reviewer_id": "reviewer-001"},
    )
    assert r2.status_code != 404, "reviewops/tasks/assign returned 404"

    # Submit review
    r3 = await test_app.post(
        f"/api/reviewops/tasks/{task_id}/review",
        json={"verdict": "approved", "comments": "Looks good"},
    )
    assert r3.status_code != 404, "reviewops/tasks/review returned 404"

    # Check status
    r4 = await test_app.get(f"/api/reviewops/tasks/{task_id}/status")
    assert r4.status_code != 404, "reviewops/tasks/status returned 404"
    if r4.status_code in OK:
        assert r4.json()["completed"] is True


# ---------------------------------------------------------------------------
# Edge Export flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edge_export_flow(test_app):
    """export ONNX -> list exports -> get formats."""
    # Export
    r1 = await test_app.post(
        "/api/edge/export",
        json={"model_id": "model-abc-123", "format": "onnx", "optimize": True},
    )
    assert r1.status_code != 404, "edge/export returned 404"

    # List exports
    r2 = await test_app.get("/api/edge/exports")
    assert r2.status_code != 404, "edge/exports returned 404"

    # Get formats
    r3 = await test_app.get("/api/edge/formats")
    assert r3.status_code != 404, "edge/formats returned 404"
    if r3.status_code in OK:
        formats = r3.json()
        assert len(formats) >= 3
        names = [f["name"] for f in formats]
        assert "onnx" in names


# ---------------------------------------------------------------------------
# Fleet Management flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fleet_management_flow(test_app, _database):
    """register device -> heartbeat -> get health."""
    await requires_postgres()
    workspace_id = _database

    # Register. jetson-nano is not a supported device type; jetson_nano is.
    r1 = await test_app.post(
        f"/api/fleet/devices?workspace_id={workspace_id}",
        json={
            "name": "edge-node-01",
            "device_type": "jetson_nano",
            "location": "warehouse-A",
        },
    )
    assert r1.status_code != 404, "fleet/devices POST returned 404"
    device_id = r1.json()["device_id"]

    # Heartbeat
    r2 = await test_app.post(
        f"/api/fleet/devices/{device_id}/heartbeat",
        json={"cpu_percent": 45.2, "memory_percent": 62.0, "inference_count": 150},
    )
    assert r2.status_code != 404, "fleet/devices/heartbeat returned 404"

    # Health
    r3 = await test_app.get(f"/api/fleet/health?workspace_id={workspace_id}")
    assert r3.status_code != 404, "fleet/health returned 404"
    if r3.status_code in OK:
        data = r3.json()
        assert "total_devices" in data
        assert data["total_devices"] == 1


# ---------------------------------------------------------------------------
# Plugin flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plugin_flow(test_app, _database):
    """register plugin -> enable -> list -> execute."""
    await requires_postgres()
    workspace_id = _database

    # Register
    r1 = await test_app.post(
        f"/api/plugins/register?workspace_id={workspace_id}",
        json={"name": "auto-label", "version": "1.0.0", "description": "Automatic labeling"},
    )
    assert r1.status_code != 404, "plugins/register returned 404"
    plugin_id = r1.json().get("id", "p1") if r1.status_code in OK else "p1"

    # Enable
    r2 = await test_app.post(f"/api/plugins/{plugin_id}/enable")
    assert r2.status_code != 404, "plugins/enable returned 404"

    # List
    r3 = await test_app.get("/api/plugins/")
    assert r3.status_code != 404, "plugins list returned 404"

    # Execute
    r4 = await test_app.post(
        f"/api/plugins/{plugin_id}/execute",
        json={"action": "label-batch", "params": {"dataset_id": "ds-001"}},
    )
    assert r4.status_code != 404, "plugins/execute returned 404"
    if r4.status_code in OK:
        assert r4.json()["status"] == "executed"


# ---------------------------------------------------------------------------
# Vertical Packs flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vertical_pack_flow(test_app):
    """list packs -> install security -> verify resources."""
    # List packs
    r1 = await test_app.get("/api/verticals/packs")
    assert r1.status_code != 404, "verticals/packs returned 404"
    if r1.status_code in OK:
        packs = r1.json()
        assert len(packs) >= 5

    # Install security pack
    r2 = await test_app.post(
        "/api/verticals/install",
        json={"pack_id": "security"},
    )
    assert r2.status_code != 404, "verticals/install returned 404"

    # Get resources
    r3 = await test_app.get("/api/verticals/packs/security/resources")
    assert r3.status_code != 404, "verticals/packs/security/resources returned 404"
    if r3.status_code in OK:
        assert "total_resources" in r3.json()


# ---------------------------------------------------------------------------
# Federated Learning flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_federated_flow(test_app):
    """create federation -> join -> start round."""
    # Create
    r1 = await test_app.post(
        "/api/federated/federations",
        json={"name": "defect-detection-fed", "model_id": "model-001", "min_participants": 2, "rounds": 5},
    )
    assert r1.status_code != 404, "federated/federations POST returned 404"
    fed_id = r1.json().get("id", "f1") if r1.status_code in OK else "f1"

    # Join (participant 1)
    r2 = await test_app.post(
        f"/api/federated/federations/{fed_id}/join",
        json={"participant_id": "site-a", "participant_name": "Factory A", "data_size": 10000},
    )
    assert r2.status_code != 404, "federated/join returned 404"

    # Join (participant 2)
    r3 = await test_app.post(
        f"/api/federated/federations/{fed_id}/join",
        json={"participant_id": "site-b", "participant_name": "Factory B", "data_size": 8000},
    )
    assert r3.status_code != 404

    # Start round
    r4 = await test_app.post(f"/api/federated/federations/{fed_id}/start-round", json={})
    assert r4.status_code != 404, "federated/start-round returned 404"
    if r4.status_code in OK:
        assert r4.json()["round"] == 1


# ---------------------------------------------------------------------------
# Mobile Backend flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mobile_flow(test_app):
    """get dashboard -> register push -> create field note."""
    # Dashboard
    r1 = await test_app.get("/api/mobile/dashboard")
    assert r1.status_code != 404, "mobile/dashboard returned 404"
    if r1.status_code in OK:
        assert "system_status" in r1.json()

    # Register push
    r2 = await test_app.post(
        "/api/mobile/push/register",
        json={"device_token": "fcm-token-abc123", "platform": "android", "user_id": "user-001"},
    )
    assert r2.status_code != 404, "mobile/push/register returned 404"

    # Create field note
    r3 = await test_app.post(
        "/api/mobile/field-notes",
        json={"title": "Site inspection", "content": "Camera 3 needs repositioning", "tags": ["maintenance"]},
    )
    assert r3.status_code != 404, "mobile/field-notes POST returned 404"
    if r3.status_code in OK:
        assert "id" in r3.json()


# ---------------------------------------------------------------------------
# SDK endpoints accessible
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sdk_endpoints_accessible(test_app):
    """Verify Python SDK / JS SDK developer endpoints exist."""
    r1 = await test_app.get("/api/developer/sdks")
    assert r1.status_code != 404, "developer/sdks returned 404"
    if r1.status_code in OK:
        sdks = r1.json()
        languages = [s["language"] for s in sdks]
        assert "python" in languages
        assert "javascript" in languages


# ---------------------------------------------------------------------------
# Developer Tools flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_developer_tools(test_app):
    """get openapi spec -> get proto file -> create node template."""
    # OpenAPI spec
    r1 = await test_app.get("/api/developer/openapi")
    assert r1.status_code != 404, "developer/openapi returned 404"
    if r1.status_code in OK:
        spec = r1.json()
        assert "openapi" in spec or "paths" in spec

    # Proto file
    r2 = await test_app.get("/api/developer/proto")
    assert r2.status_code != 404, "developer/proto returned 404"
    if r2.status_code in OK:
        assert "services" in r2.json()

    # Create node template
    r3 = await test_app.post(
        "/api/developer/node-templates",
        json={"name": "custom-resize", "node_type": "transform", "description": "Custom resize node"},
    )
    assert r3.status_code != 404, "developer/node-templates POST returned 404"


# ---------------------------------------------------------------------------
# Full platform health
# ---------------------------------------------------------------------------


V3_ENDPOINTS_GET = [
    "/api/health",
    "/api/metrics",
    "/api/knowledge-graph/nodes",
    "/api/knowledge-graph/edges",
    "/api/semantic-memory/memories",
    "/api/command-center/streams",
    "/api/command-center/dashboard",
    "/api/simulation/scenarios",
    "/api/reviewops/tasks",
    "/api/edge/exports",
    "/api/edge/formats",
    "/api/fleet/devices",
    "/api/fleet/health",
    "/api/plugins/",
    "/api/plugins/marketplace/featured",
    "/api/verticals/packs",
    "/api/verticals/installed",
    "/api/federated/federations",
    "/api/mobile/dashboard",
    "/api/mobile/field-notes",
    "/api/developer/sdks",
    "/api/developer/proto",
    "/api/developer/health",
    "/api/developer/node-templates",
    "/api/observability/dashboard",
    "/api/runtime/gpu",
    "/api/runtime/cache/stats",
    "/api/runtime/schedule",
    "/api/integrations/events",
]


@pytest.mark.asyncio
async def test_full_platform_health(test_app, _database):
    """Hit /api/health and verify all Phase 4 services are reachable (no 404s)."""
    await requires_postgres()
    # Core health
    r = await test_app.get("/api/health")
    assert r.status_code != 404, "GET /api/health returned 404"

    # All V3 endpoints
    for path in V3_ENDPOINTS_GET:
        r = await test_app.get(path)
        assert r.status_code != 404, f"GET {path} returned 404"
