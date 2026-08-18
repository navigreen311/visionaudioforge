"""Tests for VisionAudioForge Python SDK."""

import pytest
import httpx
import respx
from respx.patterns import M

from visionaudioforge import VAFClient
from visionaudioforge.exceptions import (
    AuthenticationError,
    NotFoundError,
    ServerError,
    VAFError,
)


BASE = "http://localhost:8000"


# ---------- Client creation ----------


@pytest.mark.asyncio
async def test_client_creation():
    """VAFClient stores config and creates an httpx client."""
    client = VAFClient(base_url=BASE, api_key="test-key")
    assert client.base_url == BASE
    assert client.api_key == "test-key"
    assert client.token is None
    assert client._http is not None
    await client.close()


@pytest.mark.asyncio
async def test_auth_header_api_key():
    """API key is sent via X-API-Key header."""
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        client = VAFClient(base_url=BASE, api_key="my-key")
        await client.health()
        assert route.called
        request = route.calls[0].request
        assert request.headers["X-API-Key"] == "my-key"
        await client.close()


@pytest.mark.asyncio
async def test_auth_header_bearer_token():
    """Bearer token takes precedence over API key."""
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        client = VAFClient(base_url=BASE, api_key="my-key", token="jwt-token")
        await client.health()
        request = route.calls[0].request
        assert request.headers["Authorization"] == "Bearer jwt-token"
        assert "X-API-Key" not in request.headers
        await client.close()


# ---------- Vision ----------


@pytest.mark.asyncio
async def test_vision_analyze_builds_request(tmp_path):
    """VisionClient.analyze sends file + operations to the correct endpoint."""
    img = tmp_path / "test.jpg"
    img.write_bytes(b"\xff\xd8fake-image")

    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/api/vision/analyze").mock(
            return_value=httpx.Response(200, json={"detections": [], "metadata": {}})
        )
        client = VAFClient(base_url=BASE, api_key="k")
        result = await client.vision.analyze(str(img), ["detect", "ocr"])
        assert route.called
        assert result.detections == []
        await client.close()


# ---------- Audio ----------


@pytest.mark.asyncio
async def test_audio_analyze_builds_request(tmp_path):
    """AudioClient.analyze sends file + operations."""
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"RIFF" + b"\x00" * 40)

    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/api/audio/analyze").mock(
            return_value=httpx.Response(
                200,
                json={"duration": 3.5, "sample_rate": 44100, "channels": 2, "features": {}},
            )
        )
        client = VAFClient(base_url=BASE, api_key="k")
        result = await client.audio.analyze(str(audio))
        assert route.called
        assert result.duration == 3.5
        assert result.sample_rate == 44100
        await client.close()


# ---------- Search ----------


@pytest.mark.asyncio
async def test_search_query_builds_request():
    """SearchClient.query sends JSON body for text-only search."""
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/api/search/query").mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"asset_id": "a1", "score": 0.95, "metadata": {}}]},
            )
        )
        client = VAFClient(base_url=BASE, api_key="k")
        results = await client.search.query(text="sunset", k=5)
        assert route.called
        assert len(results) == 1
        assert results[0].asset_id == "a1"
        assert results[0].score == 0.95
        await client.close()


# ---------- Pipeline ----------


@pytest.mark.asyncio
async def test_pipeline_create():
    """PipelineClient.create sends correct payload."""
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/api/pipeline/create").mock(
            return_value=httpx.Response(
                200,
                json={"id": "p1", "name": "ingest", "definition": {"steps": []}, "status": "created"},
            )
        )
        client = VAFClient(base_url=BASE, api_key="k")
        pipeline = await client.pipeline.create("ingest", {"steps": []})
        assert route.called
        assert pipeline.id == "p1"
        assert pipeline.name == "ingest"
        await client.close()


# ---------- Error handling ----------


@pytest.mark.asyncio
async def test_error_handling_401():
    """401 responses raise AuthenticationError."""
    with respx.mock(base_url=BASE) as mock:
        mock.get("/api/v1/health").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid token"})
        )
        client = VAFClient(base_url=BASE)
        with pytest.raises(AuthenticationError) as exc_info:
            await client.health()
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.message
        await client.close()


@pytest.mark.asyncio
async def test_error_handling_404():
    """404 responses raise NotFoundError."""
    with respx.mock(base_url=BASE) as mock:
        mock.get("/api/experiments/missing").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        client = VAFClient(base_url=BASE, api_key="k")
        with pytest.raises(NotFoundError) as exc_info:
            await client.models.get_experiment("missing")
        assert exc_info.value.status_code == 404
        await client.close()


@pytest.mark.asyncio
async def test_error_handling_500():
    """500 responses raise ServerError."""
    with respx.mock(base_url=BASE) as mock:
        mock.get("/api/v1/health").mock(
            return_value=httpx.Response(500, json={"detail": "Internal error"})
        )
        client = VAFClient(base_url=BASE)
        with pytest.raises(ServerError) as exc_info:
            await client.health()
        assert exc_info.value.status_code == 500
        await client.close()


# ---------- Context manager ----------


@pytest.mark.asyncio
async def test_context_manager():
    """VAFClient works as an async context manager."""
    with respx.mock(base_url=BASE) as mock:
        mock.get("/api/v1/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        async with VAFClient(base_url=BASE, api_key="k") as client:
            result = await client.health()
            assert result == {"status": "ok"}
        # After exit, the httpx client should be closed
        assert client._http.is_closed
