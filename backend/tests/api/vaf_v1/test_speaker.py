"""Tests for VAF v1 speaker-ID endpoints."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.anyio
async def test_enroll_happy_path(test_app, vaf_headers, tiny_audio):
    files = [
        ("sample_0", ("s0.wav", tiny_audio, "audio/wav")),
        ("sample_1", ("s1.wav", tiny_audio, "audio/wav")),
        ("sample_2", ("s2.wav", tiny_audio, "audio/wav")),
    ]
    data = {"userId": "user-abc"}
    resp = await test_app.post(
        "/api/v1/speaker/enroll", headers=vaf_headers, files=files, data=data
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["userId"] == "user-abc"
    assert body["enrolled"] is True
    assert body["qualityScores"] == [0.9, 0.92, 0.88]
    assert len(body["sampleUrls"]) == 3
    assert "enrolledAt" in body and body["enrolledAt"]


@pytest.mark.anyio
async def test_enroll_missing_samples_returns_422(test_app, vaf_headers, tiny_audio):
    files = [("sample_0", ("s0.wav", tiny_audio, "audio/wav"))]
    data = {"userId": "user-abc"}
    resp = await test_app.post(
        "/api/v1/speaker/enroll", headers=vaf_headers, files=files, data=data
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_verify_default_match(test_app, vaf_headers, tiny_audio):
    files = {"audio": ("v.wav", tiny_audio, "audio/wav")}
    data = {"userId": "user-abc"}
    resp = await test_app.post(
        "/api/v1/speaker/verify", headers=vaf_headers, files=files, data=data
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["match"] is True
    assert body["confidence"] == 0.92
    assert body["threshold"] == 0.85
    assert body["antiSpoofResult"]["isLiveVoice"] is True
    assert body["antiSpoofResult"]["isNotSynthesized"] is True


@pytest.mark.anyio
async def test_verify_simulate_spoof(test_app, vaf_headers, tiny_audio):
    files = {"audio": ("v.wav", tiny_audio, "audio/wav")}
    data = {"userId": "user-abc"}
    resp = await test_app.post(
        "/api/v1/speaker/verify?simulate=spoof",
        headers=vaf_headers, files=files, data=data,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["antiSpoofResult"]["isLiveVoice"] is False
    assert body["match"] is False


@pytest.mark.anyio
async def test_verify_simulate_mismatch(test_app, vaf_headers, tiny_audio):
    files = {"audio": ("v.wav", tiny_audio, "audio/wav")}
    data = {"userId": "user-abc"}
    resp = await test_app.post(
        "/api/v1/speaker/verify?simulate=mismatch",
        headers=vaf_headers, files=files, data=data,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["match"] is False
    assert body["confidence"] == 0.5


@pytest.mark.anyio
async def test_continuous_create(test_app, vaf_headers):
    payload = {
        "userId": "user-abc",
        "threshold": 0.85,
        "checkIntervalSeconds": 30,
        "enableAntiSpoof": True,
    }
    resp = await test_app.post(
        "/api/v1/speaker/continuous/create", headers=vaf_headers, json=payload
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "sessionId" in body and "websocketUrl" in body


@pytest.mark.anyio
async def test_delete_voiceprint(test_app, vaf_headers):
    resp = await test_app.delete(
        "/api/v1/speaker/user-abc", headers=vaf_headers
    )
    assert resp.status_code == 204
    # 204 must have empty body
    assert resp.content in (b"", b"null")
