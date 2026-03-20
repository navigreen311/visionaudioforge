"""Tests for health, metrics, and observability middleware."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health_returns_200_when_healthy(client: AsyncClient):
    """Health endpoint should return 200 even if backing services are unreachable."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_health_response_shape(client: AsyncClient):
    """Response must include required top-level keys and per-service structure."""
    resp = await client.get("/api/health")
    data = resp.json()

    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "version" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data

    services = data["services"]
    for svc_name in ("database", "redis", "minio"):
        assert svc_name in services
        assert "status" in services[svc_name]


@pytest.mark.anyio
async def test_request_id_header_present(client: AsyncClient):
    """Every response must carry an X-Request-ID header."""
    resp = await client.get("/api/health")
    assert "x-request-id" in resp.headers


@pytest.mark.anyio
async def test_timing_header_present(client: AsyncClient):
    """Every response must carry an X-Process-Time header."""
    resp = await client.get("/api/health")
    assert "x-process-time" in resp.headers
    # Value should be a numeric string (milliseconds)
    float(resp.headers["x-process-time"])


@pytest.mark.anyio
async def test_metrics_endpoint_returns_prometheus_format(client: AsyncClient):
    """GET /api/metrics must return Prometheus text exposition format."""
    resp = await client.get("/api/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "") or \
           "text/plain" in resp.headers.get("Content-Type", "") or \
           "openmetrics" in resp.headers.get("content-type", "")
    # Should contain at least one metric we defined
    body = resp.text
    assert "http_requests_total" in body or "http_request_duration" in body or "HELP" in body
