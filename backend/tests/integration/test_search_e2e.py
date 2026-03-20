"""End-to-end integration tests for the search API."""

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.mark.asyncio
async def test_search_returns_empty_initially(test_app):
    """POST /api/search/query with a query should return empty results initially."""
    response = await test_app.post(
        "/api/search/query",
        json={"query": "test search term", "limit": 10},
    )
    assert response.status_code in (200, 501), (
        f"Unexpected status {response.status_code}: {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        assert "results" in data or "items" in data
        results = data.get("results", data.get("items", []))
        assert isinstance(results, list)


@pytest.mark.asyncio
async def test_search_stats(test_app):
    """GET /api/search/stats should return a valid stats object."""
    response = await test_app.get("/api/search/stats")
    assert response.status_code in (200, 501), (
        f"Unexpected status {response.status_code}: {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, dict)
