"""Tests for VAF v1 TTS endpoints."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.anyio
async def test_voices_catalog(test_app, vaf_headers):
    resp = await test_app.get("/api/v1/tts/voices", headers=vaf_headers)
    assert resp.status_code == 200, resp.text
    voices = resp.json()
    assert isinstance(voices, list)
    assert len(voices) >= 4

    required_keys = {
        "id", "name", "gender", "language", "accent", "style",
        "previewUrl", "isCloned",
    }
    for v in voices:
        assert required_keys.issubset(v.keys()), v

    # Spec asks for at least one cloned voice in the catalog.
    assert any(v["isCloned"] for v in voices)


@pytest.mark.anyio
async def test_synthesize_returns_audio_with_headers(test_app, vaf_headers):
    payload = {
        "text": "Hello from Shadow.",
        "voice": "vaf-pro-female-01",
        "speed": 1.0,
        "pitch": 0,
        "emotion": "neutral",
        "format": "mp3",
        "sampleRate": 24000,
        "streaming": False,
    }
    resp = await test_app.post(
        "/api/v1/tts/synthesize", headers=vaf_headers, json=payload
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("content-type", "").startswith("audio/mpeg")
    assert "x-audio-duration" in resp.headers
    assert "x-latency-ms" in resp.headers
    float(resp.headers["x-audio-duration"])
    float(resp.headers["x-latency-ms"])
    assert len(resp.content) > 0


@pytest.mark.anyio
async def test_synthesize_missing_text_returns_422(test_app, vaf_headers):
    payload = {"voice": "vaf-pro-female-01"}  # text missing
    resp = await test_app.post(
        "/api/v1/tts/synthesize", headers=vaf_headers, json=payload
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_tts_stream_create(test_app, vaf_headers):
    payload = {"voice": "vaf-pro-female-01", "speed": 1.0, "emotion": "warm"}
    resp = await test_app.post(
        "/api/v1/tts/stream/create", headers=vaf_headers, json=payload
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "sessionId" in body and "websocketUrl" in body
    assert body["sessionId"] in body["websocketUrl"]
