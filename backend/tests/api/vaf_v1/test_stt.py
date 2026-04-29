"""Tests for VAF v1 STT endpoints."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.anyio
async def test_transcribe_happy_path(test_app, vaf_headers, tiny_audio):
    files = {"audio": ("clip.webm", tiny_audio, "audio/webm")}
    data = {"language": "en-US", "model": "accurate"}
    resp = await test_app.post(
        "/api/v1/stt/transcribe", headers=vaf_headers, files=files, data=data
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Spec contract: camelCase keys
    assert body["text"] == "[mock transcription]"
    assert body["confidence"] == 0.95
    assert body["isFinal"] is True
    assert body["language"] == "en-US"
    assert "latencyMs" in body
    assert isinstance(body["words"], list) and body["words"], body
    word0 = body["words"][0]
    for key in ("word", "start", "end", "confidence"):
        assert key in word0


@pytest.mark.anyio
async def test_transcribe_missing_audio_returns_422(test_app, vaf_headers):
    resp = await test_app.post(
        "/api/v1/stt/transcribe",
        headers=vaf_headers,
        data={"language": "en-US", "model": "accurate"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_transcribe_requires_bearer(test_app, tiny_audio):
    files = {"audio": ("clip.webm", tiny_audio, "audio/webm")}
    resp = await test_app.post("/api/v1/stt/transcribe", files=files)
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_stt_stream_create_happy_path(test_app, vaf_headers):
    payload = {
        "language": "en-US",
        "model": "realtime",
        "enableSpeakerDiarization": True,
        "customVocabulary": ["MedLink", "ChamberForge"],
        "complianceMode": ["HIPAA"],
        "interimResults": True,
        "punctuation": True,
        "profanityFilter": False,
    }
    resp = await test_app.post(
        "/api/v1/stt/stream/create", headers=vaf_headers, json=payload
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "sessionId" in body and body["sessionId"]
    assert body["websocketUrl"].startswith("ws://")
    assert body["sessionId"] in body["websocketUrl"]
