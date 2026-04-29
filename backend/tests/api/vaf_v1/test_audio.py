"""Tests for VAF v1 audio-quality endpoint."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.anyio
async def test_quality_default_good(test_app, vaf_headers, tiny_audio):
    files = {"audio": ("clip.wav", tiny_audio, "audio/wav")}
    data = {"enhance": "true", "denoise": "true", "removeEcho": "true"}
    resp = await test_app.post(
        "/api/v1/audio/quality", headers=vaf_headers, files=files, data=data
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recommendation"] == "good"
    assert body["bandwidth"] == "wideband"
    assert body["echoDetected"] is False
    assert body["noiseLevel"] == 0.2
    assert body["signalToNoise"] == 28.0
    assert body["packetLoss"] == 0.0
    assert body["clippingDetected"] is False


@pytest.mark.anyio
async def test_quality_simulate_poor(test_app, vaf_headers, tiny_audio):
    files = {"audio": ("clip.wav", tiny_audio, "audio/wav")}
    resp = await test_app.post(
        "/api/v1/audio/quality?simulate=poor", headers=vaf_headers, files=files
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recommendation"] == "switch_to_text"
    assert body["noiseLevel"] >= 0.8
    assert body["echoDetected"] is True


@pytest.mark.anyio
async def test_quality_missing_audio_returns_422(test_app, vaf_headers):
    resp = await test_app.post("/api/v1/audio/quality", headers=vaf_headers)
    assert resp.status_code == 422
