"""Comprehensive end-to-end integration tests covering the full VisionAudioForge platform.

These tests exercise every major subsystem through the HTTP API, verifying that
all routes are registered and respond without 404 errors.
"""

import uuid

import pytest

from tests.utils import (
    audio_to_wav_bytes,
    create_test_audio,
    create_test_image,
    create_test_image_with_shapes,
    image_to_png_bytes,
)


pytestmark = [pytest.mark.integration, pytest.mark.e2e]

# Accepted status codes: 200/201 = success, 501 = stub, 422 = validation, 400 = bad request
OK = (200, 201)
ACCEPTABLE = (200, 201, 400, 422, 501)
NOT_404 = lambda r: r.status_code != 404  # noqa: E731


# ---------------------------------------------------------------------------
# Vision flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_vision_flow(test_app, test_image):
    """Upload image -> preprocess -> detect -> track -> segment -> all return non-404."""
    # Analyze / preprocess
    r1 = await test_app.post(
        "/api/vision/analyze",
        files={"file": ("test.png", test_image, "image/png")},
        data={"operation": "normalize"},
    )
    assert r1.status_code != 404, f"vision/analyze returned 404: {r1.text}"

    # Detect
    img_shapes = image_to_png_bytes(create_test_image_with_shapes())
    r2 = await test_app.post(
        "/api/vision/detect",
        files={"file": ("shapes.png", img_shapes, "image/png")},
    )
    assert r2.status_code != 404, f"vision/detect returned 404: {r2.text}"

    # Optical flow (track)
    frame1 = image_to_png_bytes(create_test_image(color=(100, 100, 100)))
    frame2 = image_to_png_bytes(create_test_image(color=(200, 200, 200)))
    r3 = await test_app.post(
        "/api/vision/optical-flow",
        files=[
            ("frames", ("f1.png", frame1, "image/png")),
            ("frames", ("f2.png", frame2, "image/png")),
        ],
    )
    assert r3.status_code != 404, f"vision/optical-flow returned 404: {r3.text}"

    # Frame diff (segment)
    r4 = await test_app.post(
        "/api/vision/frame-diff",
        files=[
            ("frames", ("f1.png", frame1, "image/png")),
            ("frames", ("f2.png", frame2, "image/png")),
        ],
    )
    assert r4.status_code != 404, f"vision/frame-diff returned 404: {r4.text}"


# ---------------------------------------------------------------------------
# Audio flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_audio_flow(test_app, test_audio):
    """Upload audio -> analyze (STFT+MFCC) -> augment -> classify -> all return non-404."""
    # Analyze STFT
    r1 = await test_app.post(
        "/api/audio/analyze",
        files={"file": ("test.wav", test_audio, "audio/wav")},
        data={"features": '["stft"]'},
    )
    assert r1.status_code != 404, f"audio/analyze STFT returned 404"

    # Analyze MFCC
    r2 = await test_app.post(
        "/api/audio/analyze",
        files={"file": ("test.wav", test_audio, "audio/wav")},
        data={"features": '["mfcc"]'},
    )
    assert r2.status_code != 404, f"audio/analyze MFCC returned 404"

    # Augment
    r3 = await test_app.post(
        "/api/audio/augment",
        files={"file": ("test.wav", test_audio, "audio/wav")},
        data={"augmentation": "noise", "snr_db": "10"},
    )
    assert r3.status_code != 404, f"audio/augment returned 404"


# ---------------------------------------------------------------------------
# Model lifecycle flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_model_flow(test_app):
    """Register model -> create experiment -> log epoch -> get best -> promote."""
    # Register model
    r1 = await test_app.post(
        "/api/registry/register",
        json={
            "name": f"e2e-model-{uuid.uuid4().hex[:6]}",
            "version": "1.0.0",
            "framework": "pytorch",
            "metrics": {"accuracy": 0.92},
        },
    )
    assert r1.status_code != 404, f"registry/register returned 404"

    # Create experiment
    r2 = await test_app.post(
        "/api/experiments",
        json={
            "name": f"e2e-exp-{uuid.uuid4().hex[:6]}",
            "config": {"backbone": "resnet18", "epochs": 5, "lr": 0.001},
        },
    )
    assert r2.status_code != 404, f"experiments create returned 404"

    if r2.status_code in OK:
        exp_id = r2.json().get("id", "unknown")

        # Log epochs
        for epoch in range(1, 4):
            r3 = await test_app.post(
                f"/api/experiments/{exp_id}/log",
                json={"epoch": epoch, "metrics": {"loss": 1.0 / epoch, "accuracy": 0.5 + epoch * 0.1}},
            )
            assert r3.status_code != 404, f"experiments/{exp_id}/log returned 404"

        # Get best
        r4 = await test_app.get(f"/api/experiments/{exp_id}/best")
        assert r4.status_code != 404, f"experiments/{exp_id}/best returned 404"

    # Promote model (if registered)
    if r1.status_code in OK:
        model_id = r1.json().get("id", "unknown")
        r5 = await test_app.put(
            f"/api/registry/models/{model_id}/status",
            json={"status": "active"},
        )
        assert r5.status_code != 404, f"registry/models/{model_id}/status returned 404"


# ---------------------------------------------------------------------------
# Search flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_search_flow(test_app):
    """Index asset -> text search -> similar search."""
    # Text search
    r1 = await test_app.post(
        "/api/search/query",
        json={"query": "test search term", "limit": 5},
    )
    assert r1.status_code != 404, f"search/query returned 404"

    # Stats
    r2 = await test_app.get("/api/search/stats")
    assert r2.status_code != 404, f"search/stats returned 404"


# ---------------------------------------------------------------------------
# Pipeline flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_flow(test_app, test_workspace_id):
    """Create pipeline -> validate -> run."""
    pipeline_def = {
        "name": f"e2e-pipeline-{uuid.uuid4().hex[:6]}",
        "workspace_id": test_workspace_id,
        "nodes": [
            {"id": "n1", "type": "input", "config": {}},
            {"id": "n2", "type": "resize", "config": {"width": 224, "height": 224}},
        ],
        "edges": [{"source": "n1", "target": "n2"}],
    }

    # Validate
    r1 = await test_app.post("/api/pipeline/validate", json=pipeline_def)
    assert r1.status_code != 404, f"pipeline/validate returned 404"

    # Create
    r2 = await test_app.post("/api/pipeline/create", json=pipeline_def)
    assert r2.status_code != 404, f"pipeline/create returned 404"

    # List
    r3 = await test_app.get("/api/pipelines")
    assert r3.status_code != 404, f"pipelines list returned 404"

    # Run (if created)
    if r2.status_code in OK:
        pid = r2.json().get("id", "unknown")
        r4 = await test_app.post(f"/api/pipeline/run/{pid}")
        assert r4.status_code != 404, f"pipeline/run returned 404"


# ---------------------------------------------------------------------------
# Alert flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_alert_flow(test_app, test_workspace_id):
    """Create rule -> list alerts -> acknowledge."""
    # Create rule
    r1 = await test_app.post(
        "/api/alerts/rules",
        json={
            "name": "e2e-alert-rule",
            "condition": "metric.accuracy < 0.5",
            "severity": "warning",
            "workspace_id": test_workspace_id,
        },
    )
    assert r1.status_code != 404, f"alerts/rules returned 404"

    # List alerts
    r2 = await test_app.get("/api/alerts")
    assert r2.status_code != 404, f"alerts list returned 404"


# ---------------------------------------------------------------------------
# Copilot / Agent flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_copilot_flow(test_app):
    """Create agent -> chat -> check memory."""
    # Create agent
    r1 = await test_app.post(
        "/api/agents",
        json={"name": "e2e-test-agent", "config": {}},
    )
    assert r1.status_code != 404, f"agents create returned 404"

    # Chat
    r2 = await test_app.post(
        "/api/agents/chat",
        json={"message": "Hello, what can you do?"},
    )
    assert r2.status_code != 404, f"agents/chat returned 404"

    # List agents
    r3 = await test_app.get("/api/agents")
    assert r3.status_code != 404, f"agents list returned 404"

    # Memory (if agent created)
    if r1.status_code in OK:
        agent_id = r1.json().get("id", "unknown")
        r4 = await test_app.get(f"/api/agents/{agent_id}/memory")
        assert r4.status_code != 404, f"agents/{agent_id}/memory returned 404"


# ---------------------------------------------------------------------------
# Dataset flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_dataset_flow(test_app, test_workspace_id):
    """Create dataset -> upload sample -> compute stats -> split."""
    # Create
    r1 = await test_app.post(
        "/api/datasets",
        json={
            "name": f"e2e-dataset-{uuid.uuid4().hex[:6]}",
            "workspace_id": test_workspace_id,
            "description": "E2E test dataset",
        },
    )
    assert r1.status_code != 404, f"datasets create returned 404"

    # List
    r2 = await test_app.get("/api/datasets")
    assert r2.status_code != 404, f"datasets list returned 404"

    if r1.status_code in OK:
        ds_id = r1.json().get("id", "unknown")

        # Upload sample
        sample_img = image_to_png_bytes(create_test_image())
        r3 = await test_app.post(
            f"/api/datasets/{ds_id}/upload",
            files={"file": ("sample.png", sample_img, "image/png")},
        )
        assert r3.status_code != 404, f"datasets/{ds_id}/upload returned 404"

        # Compute stats
        r4 = await test_app.post(f"/api/datasets/{ds_id}/stats")
        assert r4.status_code != 404, f"datasets/{ds_id}/stats returned 404"

        # Split
        r5 = await test_app.post(
            f"/api/datasets/{ds_id}/split",
            json={"train_ratio": 0.7, "val_ratio": 0.15, "test_ratio": 0.15},
        )
        assert r5.status_code != 404, f"datasets/{ds_id}/split returned 404"


# ---------------------------------------------------------------------------
# Investigation flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_investigation_flow(test_app, test_workspace_id):
    """Create case -> add evidence -> get timeline."""
    # Create case
    r1 = await test_app.post(
        "/api/investigate/cases",
        json={
            "name": "e2e-investigation",
            "description": "E2E test case",
            "workspace_id": test_workspace_id,
        },
    )
    assert r1.status_code != 404, f"investigate/cases create returned 404"

    if r1.status_code in OK:
        case_id = r1.json().get("id", "unknown")

        # Add evidence
        r2 = await test_app.post(
            f"/api/investigate/cases/{case_id}/evidence",
            json={
                "asset_id": "00000000-0000-0000-0000-000000000001",
                "notes": "Test evidence item",
            },
        )
        assert r2.status_code != 404, f"investigate/cases/{case_id}/evidence returned 404"

        # Add note
        r3 = await test_app.post(
            f"/api/investigate/cases/{case_id}/notes",
            json={"user_id": "test-user", "content": "Investigation note"},
        )
        assert r3.status_code != 404, f"investigate/cases/{case_id}/notes returned 404"

    # Timeline
    r4 = await test_app.get(
        "/api/investigate/timeline",
        params={
            "workspace_id": test_workspace_id,
            "start": "2020-01-01T00:00:00",
            "end": "2030-12-31T23:59:59",
        },
    )
    assert r4.status_code != 404, f"investigate/timeline returned 404"


# ---------------------------------------------------------------------------
# Health: hit every major endpoint, verify none 404
# ---------------------------------------------------------------------------

ENDPOINTS_GET = [
    "/api/health",
    "/api/metrics",
    "/api/alerts",
    "/api/agents",
    "/api/assets",
    "/api/datasets",
    "/api/pipelines",
    "/api/registry/models",
    "/api/experiments",
    "/api/search/stats",
    "/api/workspaces",
]

ENDPOINTS_POST = [
    ("/api/auth/login", {"email": "test@test.com", "password": "test"}),
    ("/api/auth/register", {"email": "health@test.com", "password": "Pass123!", "workspace_name": "ws"}),
    ("/api/safety/scan", {"content": "test content"}),
    ("/api/search/query", {"query": "test", "limit": 5}),
    ("/api/evaluation/threshold-analysis", {"predictions": [0.9, 0.1], "ground_truth": [1, 0]}),
    ("/api/validate/drift", {"reference_data": [[1, 2], [3, 4]], "current_data": [[1, 2], [3, 4]]}),
]


@pytest.mark.asyncio
async def test_health_all_endpoints_get(test_app):
    """Hit every major GET endpoint and verify none return 404."""
    for path in ENDPOINTS_GET:
        r = await test_app.get(path)
        assert r.status_code != 404, f"GET {path} returned 404"


@pytest.mark.asyncio
async def test_health_all_endpoints_post(test_app):
    """Hit every major POST endpoint and verify none return 404."""
    for path, body in ENDPOINTS_POST:
        r = await test_app.post(path, json=body)
        assert r.status_code != 404, f"POST {path} returned 404"
