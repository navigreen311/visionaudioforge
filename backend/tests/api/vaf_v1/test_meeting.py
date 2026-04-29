"""Tests for /api/v1/meeting/* (WS11)."""

from __future__ import annotations

import pytest

from .intel_router import build_intel_client


@pytest.fixture
def client():
    return build_intel_client()


def test_meeting_process_happy_path(client):
    body = {
        "audioUrl": "https://x/meeting.wav",
        "extractActionItems": True,
        "extractDecisions": True,
        "generateSummary": True,
    }
    res = client.post("/api/v1/meeting/process", json=body)
    assert res.status_code == 200, res.text
    data = res.json()

    # Three segments alternating two speakers.
    assert len(data["segments"]) == 3
    speakers = {seg["speakerId"] for seg in data["segments"]}
    assert speakers == {"spk_alice", "spk_bob"}

    # Two action items, one decision.
    assert len(data["actionItems"]) == 2
    assert len(data["decisions"]) == 1
    for item in data["actionItems"]:
        assert item["priority"] in {"high", "medium", "low"}

    # Summary present, single paragraph (no double newlines).
    assert data["summary"]
    assert "\n\n" not in data["summary"]

    # Speaker count + duration sane.
    assert data["speakerCount"] == 2
    assert data["duration"] > 0


def test_meeting_process_skips_extraction_when_flags_false(client):
    body = {
        "audioUrl": "https://x/meeting.wav",
        "extractActionItems": False,
        "extractDecisions": False,
        "generateSummary": False,
    }
    res = client.post("/api/v1/meeting/process", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["actionItems"] == []
    assert data["decisions"] == []
    assert data["summary"] == ""


def test_meeting_process_missing_audiourl_returns_422(client):
    res = client.post("/api/v1/meeting/process", json={})
    assert res.status_code == 422


def test_meeting_process_accepts_known_speakers(client):
    body = {
        "audioUrl": "https://x/meeting.wav",
        "knownSpeakers": [
            {"name": "Alice", "voiceprintId": "vp_alice"},
            {"name": "Bob", "voiceprintId": "vp_bob"},
        ],
    }
    res = client.post("/api/v1/meeting/process", json=body)
    assert res.status_code == 200
