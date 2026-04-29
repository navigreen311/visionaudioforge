"""Tests for ``GET /api/v1/health`` (VAF v1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.anyio
async def test_health_ok(test_app):
    resp = await test_app.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "mock-1.0.0"
    assert set(body["latencies"].keys()) == {"stt", "tts", "sentiment"}
    for value in body["latencies"].values():
        assert isinstance(value, (int, float))
        assert value >= 0
