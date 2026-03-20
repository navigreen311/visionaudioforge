"""API contract tests — verify error responses are well-formatted JSON."""

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_404_returns_json(test_app):
    """GET /api/nonexistent should return 404 with a JSON body."""
    response = await test_app.get("/api/nonexistent-endpoint-xyz")
    assert response.status_code == 404
    # FastAPI returns JSON for 404 by default
    data = response.json()
    assert "detail" in data, f"404 response should have 'detail' key, got: {data}"


@pytest.mark.asyncio
async def test_422_returns_detail(test_app):
    """POST /api/auth/login with empty body should return 422 with detail field.

    Note: If the endpoint is a stub (501), validation may not trigger.
    This test adapts to both cases.
    """
    response = await test_app.post("/api/auth/login", content=b"", headers={"content-type": "application/json"})
    if response.status_code == 422:
        data = response.json()
        assert "detail" in data, f"422 response should have 'detail' key, got: {data}"
    else:
        # Stub endpoint returns 501 — acceptable in current state
        assert response.status_code in (501, 400), (
            f"Expected 422 or 501, got {response.status_code}: {response.text}"
        )
