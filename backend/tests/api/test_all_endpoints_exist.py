"""API contract tests — verify every documented endpoint exists (returns non-404)."""

import pytest


pytestmark = pytest.mark.unit


ENDPOINT_CASES = [
    # (method, path, expected_statuses, description)
    ("GET", "/api/health", {200}, "health check"),
    ("POST", "/api/auth/login", {422, 501}, "auth login (missing body, not 404)"),
    ("POST", "/api/auth/register", {422, 501}, "auth register"),
    ("GET", "/api/auth/me", {401, 501}, "auth me"),
    ("POST", "/api/vision/analyze", {401, 422, 501}, "vision analyze"),
    ("POST", "/api/vision/optical-flow", {401, 422, 501}, "vision optical flow"),
    ("POST", "/api/vision/frame-diff", {401, 422, 501}, "vision frame diff"),
    ("POST", "/api/audio/analyze", {401, 422, 501}, "audio analyze"),
    ("POST", "/api/audio/augment", {401, 422, 501}, "audio augment"),
    ("GET", "/api/experiments", {200, 401, 501}, "experiments list"),
    ("POST", "/api/experiments", {401, 422, 501}, "experiments create"),
    ("POST", "/api/search/query", {401, 422, 501}, "search query"),
    ("GET", "/api/search/stats", {200, 401, 501}, "search stats"),
    ("GET", "/api/pipelines", {200, 401, 501}, "pipelines list"),
    ("GET", "/api/alerts", {200, 401, 501}, "alerts list"),
    ("POST", "/api/agents/chat", {401, 422, 501}, "agents chat"),
    ("GET", "/api/assets", {200, 401, 501}, "assets list"),
    ("POST", "/api/safety/scan", {401, 422, 501}, "safety scan"),
    ("POST", "/api/registry/register", {401, 422, 501}, "registry register"),
    ("GET", "/api/registry/models", {200, 401, 501}, "registry list models"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,expected_statuses,desc",
    ENDPOINT_CASES,
    ids=[c[3] for c in ENDPOINT_CASES],
)
async def test_endpoint_exists(test_app, method, path, expected_statuses, desc):
    """Verify endpoint returns a non-404 status, confirming it is registered."""
    if method == "GET":
        response = await test_app.get(path)
    elif method == "POST":
        response = await test_app.post(path)
    else:
        pytest.fail(f"Unsupported method: {method}")

    assert response.status_code != 404, (
        f"Endpoint {method} {path} ({desc}) returned 404 — route not registered"
    )
    assert response.status_code in expected_statuses, (
        f"Endpoint {method} {path} ({desc}): expected one of {expected_statuses}, "
        f"got {response.status_code}"
    )
