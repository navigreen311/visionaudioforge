"""Tests for /api/v1/sentiment/* (WS11)."""

from __future__ import annotations

import pytest

from .intel_router import build_intel_client


@pytest.fixture
def client():
    return build_intel_client()


# ---------------------------------------------------------------------------
# /sentiment/stream/create
# ---------------------------------------------------------------------------


def test_sentiment_stream_create_happy_path(client):
    body = {
        "callId": "call_abc123",
        "analyzeInterval": 5,
        "includeSuggestions": True,
        "alertOnHostile": True,
    }
    res = client.post("/api/v1/sentiment/stream/create", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "sessionId" in data and data["sessionId"].startswith("sent_")
    assert data["websocketUrl"].startswith("wss://")


def test_sentiment_stream_create_missing_callid_returns_422(client):
    res = client.post(
        "/api/v1/sentiment/stream/create",
        json={"analyzeInterval": 5, "includeSuggestions": True, "alertOnHostile": True},
    )
    assert res.status_code == 422


def test_sentiment_stream_create_uses_defaults(client):
    res = client.post("/api/v1/sentiment/stream/create", json={"callId": "c1"})
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# /sentiment/analyze
# ---------------------------------------------------------------------------


def test_sentiment_analyze_happy_path(client):
    res = client.post("/api/v1/sentiment/analyze", json={"audioUrl": "https://x/a.wav"})
    assert res.status_code == 200, res.text
    data = res.json()

    # Timeline: 3 points spanning 0-30s.
    assert len(data["timeline"]) == 3
    assert data["timeline"][0]["timestamp"] == 0.0
    assert data["timeline"][-1]["timestamp"] == 30.0

    # Each timeline point carries a SentimentResult.
    for point in data["timeline"]:
        s = point["sentiment"]
        assert s["overall"] in {"positive", "neutral", "negative", "hostile"}
        assert 0.0 <= s["confidence"] <= 1.0
        for key in ("anger", "frustration", "anxiety", "satisfaction", "confusion", "urgency"):
            assert key in s["emotions"]
        assert isinstance(s["riskFlags"], list)

    # Overall sentiment.
    assert data["overall"]["overall"] == "neutral"
    assert data["overall"]["emotions"]["satisfaction"] == 0.7

    # Peaks present.
    assert len(data["peaks"]) >= 1
    assert "timestamp" in data["peaks"][0]
    assert "event" in data["peaks"][0]


def test_sentiment_analyze_missing_audiourl_returns_422(client):
    res = client.post("/api/v1/sentiment/analyze", json={})
    assert res.status_code == 422
