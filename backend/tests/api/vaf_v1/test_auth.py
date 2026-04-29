"""Tests for the VAF v1 bearer-token auth dependency."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.anyio
async def test_missing_authorization_rejects_with_401(test_app):
    resp = await test_app.get("/api/v1/tts/voices")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_malformed_authorization_rejects_with_401(test_app):
    resp = await test_app.get(
        "/api/v1/tts/voices", headers={"Authorization": "Token abc"}
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_empty_bearer_rejects_with_401(test_app):
    resp = await test_app.get(
        "/api/v1/tts/voices", headers={"Authorization": "Bearer "}
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_any_nonempty_bearer_passes(test_app):
    resp = await test_app.get(
        "/api/v1/tts/voices", headers={"Authorization": "Bearer literally-anything"}
    )
    assert resp.status_code == 200
