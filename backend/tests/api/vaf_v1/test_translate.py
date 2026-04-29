"""Tests for /api/v1/translate/* (WS11)."""

from __future__ import annotations

import io

import pytest

from .intel_router import build_intel_client


@pytest.fixture
def client():
    return build_intel_client()


def _audio_upload(filename: str = "speech.wav") -> dict:
    return {"audio": (filename, io.BytesIO(b"RIFFfake-wav-bytes"), "audio/wav")}


def test_translate_speech_happy_path(client):
    res = client.post(
        "/api/v1/translate/speech",
        files=_audio_upload(),
        data={"sourceLanguage": "es", "targetLanguage": "en"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["sourceText"] == "hola"
    assert "translated from es" in data["translatedText"]
    assert data["translatedText"].endswith("hello")
    assert data["sourceLanguage"] == "es"
    assert data["confidence"] == 0.94


def test_translate_speech_auto_source_detected(client):
    res = client.post(
        "/api/v1/translate/speech",
        files=_audio_upload(),
        data={"sourceLanguage": "auto", "targetLanguage": "en"},
    )
    assert res.status_code == 200
    data = res.json()
    # Auto means the server fills in a detected language; should not echo "auto".
    assert data["sourceLanguage"] != "auto"


def test_translate_speech_missing_audio_returns_422(client):
    res = client.post(
        "/api/v1/translate/speech",
        data={"sourceLanguage": "es", "targetLanguage": "en"},
    )
    assert res.status_code == 422


def test_translate_speech_missing_target_language_returns_422(client):
    res = client.post(
        "/api/v1/translate/speech",
        files=_audio_upload(),
        data={"sourceLanguage": "es"},
    )
    assert res.status_code == 422
