"""Tests for speaker diarization, keyword spotting, and call intelligence."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.audio.diarization import SpeakerDiarizer
from app.services.audio.keyword_spotter import KeywordSpotter
from app.services.audio.call_intelligence import CallIntelligence
from tests.utils import audio_to_wav_bytes, create_test_audio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SR = 22050


def _sine_wave(freq: float = 440.0, duration: float = 1.0, sr: int = SR) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def _two_speaker_audio(sr: int = SR) -> np.ndarray:
    """Create audio that simulates two speakers using different frequencies.

    Speaker A: 300 Hz tone (seconds 0-1, 2-3, 4-5)
    Speaker B: 800 Hz tone (seconds 1-2, 3-4)
    Total: 5 seconds
    """
    parts = []
    for i in range(5):
        freq = 300.0 if i % 2 == 0 else 800.0
        # Add slight amplitude variation per speaker
        amplitude = 0.8 if i % 2 == 0 else 0.5
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        parts.append(amplitude * np.sin(2 * np.pi * freq * t).astype(np.float32))
    return np.concatenate(parts)


def _mock_transcript_segments() -> list[dict]:
    """Create mock transcript segments for testing summarization and sentiment."""
    return [
        {
            "speaker": "Speaker_0",
            "text": "I think we should decide on the new deadline. We agreed to finish by Friday.",
            "start_s": 0.0,
            "end_s": 3.0,
        },
        {
            "speaker": "Speaker_1",
            "text": "That sounds great. I will prepare the report by tomorrow.",
            "start_s": 3.0,
            "end_s": 6.0,
        },
        {
            "speaker": "Speaker_0",
            "text": "There is a problem with the current approach. We need to fix the issue.",
            "start_s": 6.0,
            "end_s": 9.0,
        },
        {
            "speaker": "Speaker_1",
            "text": "I agree. The next steps are important. Let's prioritize this action item.",
            "start_s": 9.0,
            "end_s": 12.0,
        },
    ]


# ---------------------------------------------------------------------------
# Speaker Diarization tests
# ---------------------------------------------------------------------------


class TestSpeakerDiarizer:
    def test_diarize_identifies_speakers(self):
        """Diarization should identify at least 1 speaker."""
        diarizer = SpeakerDiarizer()
        audio = _two_speaker_audio()
        result = diarizer.diarize(audio, SR)

        assert "segments" in result
        assert "num_speakers" in result
        assert "speaker_stats" in result
        assert result["num_speakers"] >= 1
        assert len(result["segments"]) >= 1

        # Each segment should have required keys
        for seg in result["segments"]:
            assert "speaker" in seg
            assert "start_s" in seg
            assert "end_s" in seg
            assert "duration_s" in seg

    def test_diarize_segments_ordered(self):
        """Diarization segments should be in chronological order."""
        diarizer = SpeakerDiarizer()
        audio = _two_speaker_audio()
        result = diarizer.diarize(audio, SR)

        segments = result["segments"]
        for i in range(1, len(segments)):
            assert segments[i]["start_s"] >= segments[i - 1]["start_s"], (
                f"Segment {i} starts before segment {i-1}"
            )

    def test_diarize_with_num_speakers(self):
        """When num_speakers is specified, should use that count."""
        diarizer = SpeakerDiarizer()
        audio = _two_speaker_audio()
        result = diarizer.diarize(audio, SR, num_speakers=2)

        assert result["num_speakers"] == 2
        speakers = set(seg["speaker"] for seg in result["segments"])
        assert len(speakers) == 2

    def test_diarize_short_audio(self):
        """Very short audio should still return a valid result."""
        diarizer = SpeakerDiarizer()
        audio = _sine_wave(440.0, duration=0.5)
        result = diarizer.diarize(audio, SR)

        assert result["num_speakers"] >= 1
        assert len(result["segments"]) >= 1

    def test_speaker_stats_present(self):
        """Speaker stats should include total_time, percentage, avg_energy."""
        diarizer = SpeakerDiarizer()
        audio = _two_speaker_audio()
        result = diarizer.diarize(audio, SR)

        for speaker, stats in result["speaker_stats"].items():
            assert "total_time" in stats
            assert "percentage" in stats
            assert "avg_energy" in stats
            assert stats["total_time"] > 0
            assert 0 <= stats["percentage"] <= 100


# ---------------------------------------------------------------------------
# Keyword Spotting tests
# ---------------------------------------------------------------------------


class TestKeywordSpotter:
    @pytest.mark.anyio
    async def test_keyword_spotting_finds_word(self):
        """Keyword spotter should find keywords in transcribed text."""
        spotter = KeywordSpotter()
        # Force STT unavailable — it returns a fallback message containing "Whisper"
        spotter._stt.available = False

        audio = _sine_wave(440.0, duration=1.0)
        results = await spotter.spot_keywords(audio, SR, ["Whisper"])

        assert len(results) >= 1
        assert results[0]["keyword"] == "Whisper"
        assert "start_s" in results[0]
        assert "end_s" in results[0]
        assert "confidence" in results[0]

    @pytest.mark.anyio
    async def test_keyword_not_present(self):
        """Keywords not in the audio should not be returned."""
        spotter = KeywordSpotter()
        spotter._stt.available = False

        audio = _sine_wave(440.0, duration=1.0)
        results = await spotter.spot_keywords(audio, SR, ["xyznonexistent"])

        assert len(results) == 0

    @pytest.mark.anyio
    async def test_empty_keywords_list(self):
        """Empty keywords list should return empty results."""
        spotter = KeywordSpotter()
        audio = _sine_wave(440.0, duration=1.0)
        results = await spotter.spot_keywords(audio, SR, [])
        assert results == []


# ---------------------------------------------------------------------------
# Call Intelligence — Action Items
# ---------------------------------------------------------------------------


class TestActionItemExtraction:
    def test_action_item_extraction(self):
        """Should extract action items from transcript segments."""
        ci = CallIntelligence()
        segments = _mock_transcript_segments()
        items = ci.extract_action_items(segments)

        assert len(items) >= 1
        for item in items:
            assert "action" in item
            assert "assignee" in item
            assert "deadline" in item
            assert "speaker" in item

    def test_action_items_with_deadline(self):
        """Should extract deadline when date pattern is present."""
        ci = CallIntelligence()
        segments = [
            {
                "speaker": "Speaker_0",
                "text": "We will deliver the prototype by 2026-03-25.",
                "start_s": 0.0,
                "end_s": 3.0,
            }
        ]
        items = ci.extract_action_items(segments)

        assert len(items) >= 1
        deadline_items = [i for i in items if i["deadline"] is not None]
        assert len(deadline_items) >= 1


# ---------------------------------------------------------------------------
# Call Intelligence — Sentiment
# ---------------------------------------------------------------------------


class TestSentimentAnalysis:
    def test_sentiment_analysis(self):
        """Should analyze sentiment per speaker."""
        ci = CallIntelligence()
        segments = _mock_transcript_segments()
        result = ci.analyze_sentiment_per_speaker(segments)

        assert "Speaker_0" in result
        assert "Speaker_1" in result

        for speaker, sentiment in result.items():
            assert "overall" in sentiment
            assert sentiment["overall"] in ("positive", "negative", "neutral")
            assert "scores" in sentiment
            scores = sentiment["scores"]
            assert "positive" in scores
            assert "negative" in scores
            assert "neutral" in scores
            assert 0 <= scores["positive"] <= 1
            assert 0 <= scores["negative"] <= 1
            assert 0 <= scores["neutral"] <= 1

    def test_positive_text_detected(self):
        """Text with mostly positive words should yield positive sentiment."""
        ci = CallIntelligence()
        segments = [
            {
                "speaker": "Speaker_0",
                "text": "This is great, excellent, wonderful, amazing, fantastic work!",
                "start_s": 0.0,
                "end_s": 3.0,
            }
        ]
        result = ci.analyze_sentiment_per_speaker(segments)
        assert result["Speaker_0"]["overall"] == "positive"

    def test_negative_text_detected(self):
        """Text with mostly negative words should yield negative sentiment."""
        ci = CallIntelligence()
        segments = [
            {
                "speaker": "Speaker_0",
                "text": "This is bad, wrong, terrible, horrible, awful, a problem and an issue.",
                "start_s": 0.0,
                "end_s": 3.0,
            }
        ]
        result = ci.analyze_sentiment_per_speaker(segments)
        assert result["Speaker_0"]["overall"] == "negative"


# ---------------------------------------------------------------------------
# Call Intelligence — Talk Ratio
# ---------------------------------------------------------------------------


class TestTalkRatio:
    def test_talk_ratio_sums_to_100(self):
        """Talk ratio percentages should sum to approximately 100%."""
        ci = CallIntelligence()
        diarizer = SpeakerDiarizer()
        audio = _two_speaker_audio()
        diarization = diarizer.diarize(audio, SR, num_speakers=2)

        ratio = ci.compute_talk_ratio(diarization)
        assert len(ratio) >= 1

        total_pct = sum(v["percentage"] for v in ratio.values())
        assert abs(total_pct - 100.0) < 1.0, f"Total percentage {total_pct} should be ~100"

        for speaker, data in ratio.items():
            assert "time_s" in data
            assert "percentage" in data
            assert "interruptions" in data
            assert data["time_s"] > 0

    def test_talk_ratio_empty_diarization(self):
        """Empty diarization should return empty ratio."""
        ci = CallIntelligence()
        ratio = ci.compute_talk_ratio({"segments": []})
        assert ratio == {}


# ---------------------------------------------------------------------------
# Call Intelligence — Meeting Summary
# ---------------------------------------------------------------------------


class TestMeetingSummary:
    def test_meeting_summary(self):
        """Should produce summary with key points and decisions."""
        ci = CallIntelligence()
        segments = _mock_transcript_segments()
        result = ci.summarize_meeting(segments)

        assert "summary" in result
        assert "key_points" in result
        assert "decisions" in result
        assert len(result["summary"]) > 0

    def test_empty_transcript_summary(self):
        """Empty transcript should return empty summary."""
        ci = CallIntelligence()
        result = ci.summarize_meeting([])
        assert result["summary"] == ""
        assert result["key_points"] == []
        assert result["decisions"] == []


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_diarize(client):
    """POST /api/audio/diarize should return diarization result."""
    audio = _two_speaker_audio()
    wav_bytes = audio_to_wav_bytes(audio, sr=SR)

    resp = await client.post(
        "/api/audio/diarize",
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "segments" in data
    assert "num_speakers" in data
    assert "speaker_stats" in data
    assert data["num_speakers"] >= 1


@pytest.mark.anyio
async def test_api_call_analysis(client):
    """POST /api/audio/call-analysis should return full analysis."""
    audio = _two_speaker_audio()
    wav_bytes = audio_to_wav_bytes(audio, sr=SR)

    resp = await client.post(
        "/api/audio/call-analysis",
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "transcript" in data
    assert "speakers" in data
    assert "summary" in data
    assert "action_items" in data
    assert "sentiment" in data
    assert "duration_s" in data
    assert "talk_ratio" in data


@pytest.mark.anyio
async def test_api_summarize(client):
    """POST /api/audio/summarize should return summary and action items."""
    segments = _mock_transcript_segments()
    resp = await client.post(
        "/api/audio/summarize",
        json={"transcript_segments": segments},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "key_points" in data
    assert "decisions" in data
    assert "action_items" in data


@pytest.mark.anyio
async def test_api_sentiment(client):
    """POST /api/audio/sentiment should return per-speaker sentiment."""
    segments = _mock_transcript_segments()
    resp = await client.post(
        "/api/audio/sentiment",
        json={"transcript_segments": segments},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "sentiment" in data
    assert "Speaker_0" in data["sentiment"]
    assert "Speaker_1" in data["sentiment"]
