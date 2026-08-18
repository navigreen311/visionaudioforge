"""Every client method exercised against a mocked transport.

The SDK shipped with one test file covering a handful of methods on a client
that claims full API coverage. This file drives every sub-client method and
pins the request path each one sends — the SDK was written against an
/api/v1/* surface that never shipped, so most calls 404'd against a real
server and no test noticed.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from visionaudioforge import VAFClient

BASE = "http://localhost:8000"


@pytest.fixture
async def client():
    async with VAFClient(base_url=BASE, api_key="test-key") as c:
        yield c


@pytest.fixture
def sample_file(tmp_path):
    """A real file on disk — the upload helpers take paths, not bytes."""
    path = tmp_path / "sample.bin"
    path.write_bytes(b"sample-content")
    return str(path)


def _route(mock: respx.MockRouter, method: str, path: str, payload=None, status=200):
    """Register a route and return it so the caller can assert on the call."""
    return mock.request(method, f"{BASE}{path}").mock(
        return_value=httpx.Response(
            status, json=payload if payload is not None else {}
        )
    )


# ---------------------------------------------------------------------------
# Client-level and credentials
# ---------------------------------------------------------------------------


@respx.mock
async def test_login_posts_to_the_real_auth_path_and_stores_the_token(client):
    """Auth lives at /api/auth/login — there is no /api/v1/auth."""
    route = _route(
        respx.mock,
        "POST",
        "/api/auth/login",
        {"access_token": "jwt-123", "refresh_token": "r", "token_type": "bearer"},
    )

    result = await client.login("a@example.com", "pw")

    assert route.called
    assert result["access_token"] == "jwt-123"
    assert client.token == "jwt-123"


@respx.mock
async def test_health(client):
    route = _route(respx.mock, "GET", "/api/v1/health", {"status": "ok"})
    assert (await client.health())["status"] == "ok"
    assert route.called


@respx.mock
async def test_api_key_is_sent_when_no_token_is_held(client):
    route = _route(respx.mock, "GET", "/api/v1/health", {"status": "ok"})
    await client.health()

    request = route.calls[0].request
    assert request.headers["X-API-Key"] == "test-key"
    assert "Authorization" not in request.headers


@respx.mock
async def test_bearer_token_takes_precedence_over_the_api_key(client):
    client.token = "jwt-123"
    route = _route(respx.mock, "GET", "/api/v1/health", {"status": "ok"})
    await client.health()

    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer jwt-123"
    # Sending both would let a stale key override the session token server-side.
    assert "X-API-Key" not in request.headers


@respx.mock
async def test_no_credentials_sends_neither_header():
    async with VAFClient(base_url=BASE) as bare:
        route = _route(respx.mock, "GET", "/api/v1/health", {"status": "ok"})
        await bare.health()

        request = route.calls[0].request
        assert "Authorization" not in request.headers
        assert "X-API-Key" not in request.headers


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------


@respx.mock
async def test_vision_methods(client, sample_file):
    analyze = _route(respx.mock, "POST", "/api/vision/analyze", {"detections": []})
    detect = _route(respx.mock, "POST", "/api/vision/detect", {"detections": []})
    flow = _route(
        respx.mock, "POST", "/api/vision/optical-flow", {"method": "farneback"}
    )
    ocr = _route(respx.mock, "POST", "/api/vision/ocr", {"text": "hello"})
    segment = _route(respx.mock, "POST", "/api/vision/segment", {"masks": []})
    track = _route(respx.mock, "POST", "/api/vision/track", {"tracks": []})

    await client.vision.analyze(sample_file, ["detect"])
    await client.vision.detect(sample_file)
    await client.vision.optical_flow(sample_file, sample_file)
    assert (await client.vision.ocr(sample_file)).text == "hello"
    await client.vision.segment(sample_file)
    await client.vision.track([sample_file])

    assert all(r.called for r in (analyze, detect, flow, ocr, segment, track))


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------


@respx.mock
async def test_audio_methods(client, sample_file):
    analyze = _route(respx.mock, "POST", "/api/audio/analyze", {"duration": 1.0})
    transcribe = _route(
        respx.mock, "POST", "/api/audio/transcribe", {"text": "spoken"}
    )
    diarize = _route(respx.mock, "POST", "/api/audio/diarize", {"speakers": []})
    classify = _route(
        respx.mock, "POST", "/api/audio/classify", {"label": "speech", "confidence": 0.9}
    )
    respx.mock.request("POST", f"{BASE}/api/audio/augment").mock(
        return_value=httpx.Response(200, content=b"augmented-bytes")
    )

    await client.audio.analyze(sample_file)
    assert (await client.audio.transcribe(sample_file)).text == "spoken"
    await client.audio.diarize(sample_file)
    assert (await client.audio.classify(sample_file)).label == "speech"
    assert await client.audio.augment(sample_file, {"noise": 0.1}) == b"augmented-bytes"

    assert all(r.called for r in (analyze, transcribe, diarize, classify))


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


@respx.mock
async def test_asset_lifecycle(client, sample_file):
    upload = _route(
        respx.mock, "POST", "/api/assets", {"id": "a1", "name": "sample.bin"}
    )
    listing = _route(respx.mock, "GET", "/api/assets", {"items": []})
    fetch = _route(
        respx.mock, "GET", "/api/assets/a1", {"id": "a1", "name": "sample.bin"}
    )
    delete = _route(respx.mock, "DELETE", "/api/assets/a1", status=204)

    assert (await client.assets.upload(sample_file)).id == "a1"
    await client.assets.list()
    await client.assets.get("a1")
    await client.assets.delete("a1")

    assert all(r.called for r in (upload, listing, fetch, delete))


@respx.mock
async def test_asset_download_returns_raw_bytes(client):
    respx.mock.request("GET", f"{BASE}/api/assets/a1/download").mock(
        return_value=httpx.Response(200, content=b"binary-content")
    )
    assert await client.assets.download("a1") == b"binary-content"


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


@respx.mock
async def test_dataset_methods(client):
    create = _route(respx.mock, "POST", "/api/datasets", {"id": "d1", "name": "n"})
    listing = _route(respx.mock, "GET", "/api/datasets", [])
    fetch = _route(respx.mock, "GET", "/api/datasets/d1", {"id": "d1", "name": "n"})
    delete = _route(respx.mock, "DELETE", "/api/datasets/d1", status=204)
    version_create = _route(
        respx.mock,
        "POST",
        "/api/datasets/d1/versions",
        {"id": "v1", "dataset_id": "d1", "version": "1"},
    )
    version_list = _route(respx.mock, "GET", "/api/datasets/d1/versions", [])

    await client.datasets.create("name", "image")
    await client.datasets.list()
    await client.datasets.get("d1")
    await client.datasets.delete("d1")
    await client.datasets.create_version("d1", "1")
    await client.datasets.list_versions("d1")

    assert all(
        r.called
        for r in (create, listing, fetch, delete, version_create, version_list)
    )


# ---------------------------------------------------------------------------
# Models — served by /api/registry, not /api/models
# ---------------------------------------------------------------------------


@respx.mock
async def test_model_methods_target_the_registry(client):
    model = {"id": "m1", "name": "m", "version": "1.0"}
    register = _route(respx.mock, "POST", "/api/registry/models", model)
    listing = _route(respx.mock, "GET", "/api/registry/models", [])
    promote = _route(respx.mock, "PUT", "/api/registry/models/m1/status", model)
    compare = _route(respx.mock, "POST", "/api/registry/compare", {})
    train = _route(
        respx.mock, "POST", "/api/experiments", {"id": "e1", "status": "running"}
    )
    experiment = _route(respx.mock, "GET", "/api/experiments/e1", {"id": "e1"})

    await client.models.register("m", "1.0", "resnet50")
    await client.models.list()
    await client.models.promote("m1", "production")
    await client.models.compare("m1", "m2")
    await client.models.start_training({"epochs": 1})
    await client.models.get_experiment("e1")

    assert all(
        r.called for r in (register, listing, promote, compare, train, experiment)
    )


# ---------------------------------------------------------------------------
# Search, pipeline, agents, alerts, transform
# ---------------------------------------------------------------------------


@respx.mock
async def test_search_methods(client):
    query = _route(respx.mock, "POST", "/api/search/query", {"results": []})
    index = _route(
        respx.mock, "POST", "/api/search/index", {"asset_id": "a1", "status": "indexed"}
    )
    similar = _route(respx.mock, "POST", "/api/search/similar/a1", {"results": []})

    await client.search.query(text="cat")
    assert (await client.search.index("a1")).status == "indexed"
    await client.search.similar("a1")

    assert all(r.called for r in (query, index, similar))


@respx.mock
async def test_pipeline_methods(client):
    pipeline = {"id": "p1", "name": "p"}
    create = _route(respx.mock, "POST", "/api/pipeline/create", pipeline)
    run = _route(
        respx.mock,
        "POST",
        "/api/pipeline/run/p1",
        {"id": "r1", "pipeline_id": "p1", "status": "queued"},
    )
    listing = _route(respx.mock, "GET", "/api/pipeline/list", [])
    generate = _route(respx.mock, "POST", "/api/pipeline/generate", pipeline)

    await client.pipeline.create("p", {"nodes": []})
    assert (await client.pipeline.run("p1")).status == "queued"
    await client.pipeline.list()
    await client.pipeline.generate_from_description("blur faces")

    assert all(r.called for r in (create, run, listing, generate))


@respx.mock
async def test_agent_methods(client):
    chat = _route(respx.mock, "POST", "/api/agents/chat", {"response": "hi"})
    listing = _route(respx.mock, "GET", "/api/agents", [])
    memory = _route(respx.mock, "GET", "/api/agents/ag1/memory", [])

    await client.agents.chat("hello")
    await client.agents.list_agents()
    await client.agents.get_memory("ag1")

    assert all(r.called for r in (chat, listing, memory))


@respx.mock
async def test_alert_methods(client):
    alert = {"id": "al1", "type": "rule", "message": "m"}
    create = _route(respx.mock, "POST", "/api/alerts", alert)
    listing = _route(respx.mock, "GET", "/api/alerts", [])
    fetch = _route(respx.mock, "GET", "/api/alerts/al1", alert)
    dismiss = _route(respx.mock, "DELETE", "/api/alerts/al1", status=204)

    await client.alerts.create("rule", "m", "high")
    await client.alerts.list()
    assert (await client.alerts.get("al1")).id == "al1"
    await client.alerts.dismiss("al1")

    assert all(r.called for r in (create, listing, fetch, dismiss))


@respx.mock
async def test_transform_methods(client):
    result = {"id": "t1", "status": "done"}
    apply_route = _route(respx.mock, "POST", "/api/transform/audio", result)
    operations = _route(respx.mock, "GET", "/api/transform/presets", [])
    fetch = _route(respx.mock, "GET", "/api/transform/t1", result)

    await client.transform.apply("a1", [{"op": "denoise"}])
    await client.transform.list_operations()
    assert (await client.transform.get_result("t1")).status == "done"

    assert all(r.called for r in (apply_route, operations, fetch))


# ---------------------------------------------------------------------------
# Sub-client caching
# ---------------------------------------------------------------------------


async def test_sub_clients_are_cached(client):
    """Each property returns the same instance rather than rebuilding it."""
    for name in (
        "vision",
        "audio",
        "models",
        "search",
        "pipeline",
        "agents",
        "datasets",
        "alerts",
        "assets",
        "transform",
    ):
        assert getattr(client, name) is getattr(client, name), name
