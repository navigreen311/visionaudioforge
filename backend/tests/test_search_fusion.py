"""Tests for CLAP audio search, event fusion, saved searches, and conversational search."""

from __future__ import annotations

import io
import struct
import wave
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.services.search.embeddings import EmbeddingService
from app.services.search.fusion import EventFusionEngine
from app.services.search.saved_searches import SavedSearchService
from app.services.search.conversational import ConversationalSearch
from app.services.search.voice_query import VoiceQueryService


# ======================================================================
# Audio embedding tests
# ======================================================================


class TestAudioEmbedding:
    """Tests for CLAP / MFCC audio embeddings."""

    def setup_method(self):
        self.svc = EmbeddingService()
        # Force fallback mode so tests don't require CLAP/CLIP models
        self.svc._use_fallback = True
        self.svc._use_clap_fallback = True

    def test_audio_embedding_512_dim(self):
        """embed_audio returns a 512-dimensional vector."""
        audio = np.random.randn(16000).astype(np.float32)
        vec = self.svc.embed_audio(audio, sr=16000)
        assert vec.shape == (512,), f"Expected shape (512,), got {vec.shape}"

    def test_audio_embedding_fallback_mfcc(self):
        """MFCC fallback produces a normalised 512-dim vector."""
        audio = np.random.randn(16000).astype(np.float32)
        vec = self.svc._mfcc_embedding(audio, sr=16000)
        assert vec.shape == (512,)
        norm = float(np.linalg.norm(vec))
        assert abs(norm - 1.0) < 1e-5, f"Expected norm ≈ 1.0, got {norm}"

    def test_audio_embedding_deterministic(self):
        """Same audio input yields same MFCC embedding."""
        np.random.seed(42)
        audio = np.random.randn(16000).astype(np.float32)
        vec1 = self.svc._mfcc_embedding(audio, sr=16000)
        vec2 = self.svc._mfcc_embedding(audio, sr=16000)
        np.testing.assert_array_almost_equal(vec1, vec2)

    def test_audio_embedding_short_audio(self):
        """Short audio clips still produce valid embeddings."""
        audio = np.random.randn(100).astype(np.float32)
        vec = self.svc.embed_audio(audio, sr=16000)
        assert vec.shape == (512,)


# ======================================================================
# Event fusion tests
# ======================================================================


class TestEventFusion:
    """Tests for EventFusionEngine."""

    def setup_method(self):
        self.engine = EventFusionEngine()

    def test_event_fusion_groups_by_time(self):
        """Events within the time window are grouped together."""
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            {"timestamp": base.isoformat(), "modality": "vision", "confidence": 0.8},
            {"timestamp": (base + timedelta(seconds=2)).isoformat(), "modality": "audio", "confidence": 0.7},
            {"timestamp": (base + timedelta(seconds=20)).isoformat(), "modality": "vision", "confidence": 0.9},
        ]

        fused = self.engine.fuse_events(events, time_window_s=5.0)
        assert len(fused) == 2, f"Expected 2 fused groups, got {len(fused)}"

        # First group should have 2 events (within 5s)
        assert len(fused[0]["events"]) == 2
        assert set(fused[0]["modalities"]) == {"vision", "audio"}
        assert "fused_id" in fused[0]
        assert "confidence" in fused[0]
        assert "summary" in fused[0]

        # Second group should have 1 event
        assert len(fused[1]["events"]) == 1

    def test_event_fusion_empty(self):
        """Empty event list returns empty fused list."""
        assert self.engine.fuse_events([]) == []

    def test_event_fusion_single_event(self):
        """Single event produces single fused group."""
        events = [{"timestamp": "2025-01-01T12:00:00Z", "modality": "vision", "confidence": 0.5}]
        fused = self.engine.fuse_events(events)
        assert len(fused) == 1

    def test_event_fusion_confidence_boost(self):
        """Multi-modal fusion boosts confidence."""
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            {"timestamp": base.isoformat(), "modality": "vision", "confidence": 0.8},
            {"timestamp": (base + timedelta(seconds=1)).isoformat(), "modality": "audio", "confidence": 0.8},
        ]
        fused = self.engine.fuse_events(events, time_window_s=5.0)
        # Multi-modal boost: avg(0.8, 0.8) * 1.2 = 0.96
        assert fused[0]["confidence"] > 0.8

    def test_temporal_alignment_matches(self):
        """Vision and audio events within tolerance are matched."""
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        vision_events = [
            {"timestamp": base.isoformat(), "type": "motion"},
            {"timestamp": (base + timedelta(seconds=10)).isoformat(), "type": "person"},
        ]
        audio_events = [
            {"timestamp": (base + timedelta(milliseconds=200)).isoformat(), "type": "loud_sound"},
            {"timestamp": (base + timedelta(seconds=30)).isoformat(), "type": "speech"},
        ]

        pairs = self.engine.temporal_alignment(vision_events, audio_events, tolerance_ms=500)
        assert len(pairs) == 1
        assert pairs[0][0]["type"] == "motion"
        assert pairs[0][1]["type"] == "loud_sound"

    def test_temporal_alignment_no_match(self):
        """Events too far apart are not matched."""
        vision_events = [{"timestamp": "2025-01-01T12:00:00Z", "type": "motion"}]
        audio_events = [{"timestamp": "2025-01-01T13:00:00Z", "type": "loud_sound"}]

        pairs = self.engine.temporal_alignment(vision_events, audio_events, tolerance_ms=500)
        assert len(pairs) == 0

    def test_cross_modal_alert_triggers(self):
        """Cross-modal alert triggers when rule matches."""
        vision_event = {"type": "motion", "confidence": 0.9}
        audio_event = {"type": "loud_sound", "confidence": 0.85}
        rule = {"vision_type": "motion", "audio_type": "loud_sound", "min_confidence": 0.5}

        alert = self.engine.cross_modal_alert(vision_event, audio_event, rule)
        assert alert is not None
        assert "alert_id" in alert
        assert alert["confidence"] > 0.5
        assert "Cross-modal alert" in alert["message"]

    def test_cross_modal_alert_no_match(self):
        """Cross-modal alert returns None when rule doesn't match."""
        vision_event = {"type": "person", "confidence": 0.9}
        audio_event = {"type": "loud_sound", "confidence": 0.85}
        rule = {"vision_type": "motion", "audio_type": "loud_sound"}

        alert = self.engine.cross_modal_alert(vision_event, audio_event, rule)
        assert alert is None


# ======================================================================
# Saved searches tests
# ======================================================================


class TestSavedSearches:
    """Tests for SavedSearchService."""

    def setup_method(self):
        self.svc = SavedSearchService()

    @pytest.mark.asyncio
    async def test_saved_search_crud(self):
        """Save and list searches (in-memory fallback without DB)."""
        result = await self.svc.save_search(
            db=None,
            workspace_id="00000000-0000-0000-0000-000000000000",
            user_id="user1",
            name="Test search",
            query="person running",
            modality="text",
        )
        assert result["type"] == "saved_search"
        assert result["payload"]["query"] == "person running"
        assert result["payload"]["name"] == "Test search"
        assert result["payload"]["user_id"] == "user1"

    @pytest.mark.asyncio
    async def test_execute_saved_search(self):
        """Execute saved search returns empty list without DB."""
        results = await self.svc.execute_saved_search(
            db=None,
            search_id="00000000-0000-0000-0000-000000000001",
        )
        # Without a DB, the search won't find the saved search
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_list_saved_searches_no_db(self):
        """List returns empty list when DB is unavailable."""
        results = await self.svc.list_saved_searches(
            db=None,
            workspace_id="00000000-0000-0000-0000-000000000000",
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_delete_saved_search_no_db(self):
        """Delete returns False when DB is unavailable."""
        result = await self.svc.delete_saved_search(
            db=None,
            search_id="00000000-0000-0000-0000-000000000001",
        )
        assert result is False


# ======================================================================
# Conversational search tests
# ======================================================================


class TestConversationalSearch:
    """Tests for ConversationalSearch."""

    def setup_method(self):
        self.svc = ConversationalSearch()

    def test_conversational_context_enrichment(self):
        """Query refinement merges keywords from history."""
        query = "show me similar ones from yesterday"
        history = ["find red cars in parking lot", "zoom into camera 3"]

        refined = self.svc._refine_query(query, history)
        # The refined query should contain keywords from history
        assert refined != query  # Should be enriched
        assert "yesterday" in refined

    def test_conversational_no_history(self):
        """Without history, the query stays the same."""
        query = "person running"
        refined = self.svc._refine_query(query, [])
        assert refined == query

    def test_conversational_non_followup(self):
        """A detailed enough query is not treated as a follow-up."""
        query = "find all red vehicles in zone alpha with high confidence detection"
        history = ["some earlier query"]
        refined = self.svc._refine_query(query, history)
        assert refined == query

    @pytest.mark.asyncio
    async def test_follow_up_suggestions(self):
        """Suggestions are generated based on query and results."""
        suggestions = await self.svc.suggest_follow_ups(
            query="person running",
            results=[
                {"asset_id": "a1", "score": 0.9, "rank": 1, "asset_type": "video"},
                {"asset_id": "a2", "score": 0.8, "rank": 2, "asset_type": "video"},
            ],
        )
        assert len(suggestions) >= 3
        assert any("similar" in s.lower() for s in suggestions)
        assert any("audio" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_follow_up_suggestions_no_results(self):
        """Suggestions for empty results include 'broader' advice."""
        suggestions = await self.svc.suggest_follow_ups(
            query="nonexistent thing",
            results=[],
        )
        assert any("broader" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_search_with_context_returns_structure(self):
        """search_with_context returns dict with required keys."""
        result = await self.svc.search_with_context(
            query="person",
            conversation_history=[],
            workspace_id="00000000-0000-0000-0000-000000000000",
        )
        assert "results" in result
        assert "refined_query" in result
        assert "suggestions" in result


# ======================================================================
# Voice query tests
# ======================================================================


class TestVoiceQuery:
    """Tests for VoiceQueryService."""

    def setup_method(self):
        self.svc = VoiceQueryService()

    @pytest.mark.asyncio
    async def test_voice_query_returns_results(self):
        """Voice query produces a transcript and search results list."""
        audio = np.random.randn(16000).astype(np.float32)
        result = await self.svc.process_voice_query(audio, sr=16000)
        assert "transcript" in result
        assert "search_results" in result
        assert isinstance(result["transcript"], str)
        assert isinstance(result["search_results"], list)

    @pytest.mark.asyncio
    async def test_voice_query_stub_transcript(self):
        """Voice query always produces a non-None transcript string."""
        audio = np.random.randn(16000).astype(np.float32)
        result = await self.svc.process_voice_query(audio, sr=16000)
        assert isinstance(result["transcript"], str)


# ======================================================================
# API route tests
# ======================================================================


class TestSearchRoutes:
    """Tests for the new search API endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.routes.search import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_api_audio_query(self, client):
        """POST /api/search/audio-query accepts an audio file."""
        # Create a valid WAV file in memory
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            samples = (np.random.randn(16000) * 3000).astype(np.int16)
            wf.writeframes(samples.tobytes())
        wav_bytes = buf.getvalue()

        response = client.post(
            "/api/search/audio-query",
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
        )
        # Should return 200 (may have 0 results since index is empty)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data

    def test_api_fuse(self, client):
        """POST /api/search/fuse returns a timeline."""
        response = client.post(
            "/api/search/fuse",
            json={
                "workspace_id": "00000000-0000-0000-0000-000000000000",
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-01-02T00:00:00Z",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data

    def test_api_conversational(self, client):
        """POST /api/search/conversational returns results and suggestions."""
        response = client.post(
            "/api/search/conversational",
            json={
                "query": "person running",
                "history": [],
                "workspace_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "refined_query" in data
        assert "suggestions" in data

    def test_api_saved_search_post(self, client):
        """POST /api/search/saved creates a saved search."""
        response = client.post(
            "/api/search/saved",
            json={
                "name": "My Search",
                "query": "red car",
                "modality": "text",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "saved_search"

    def test_api_saved_search_list(self, client):
        """GET /api/search/saved returns saved searches list."""
        response = client.get("/api/search/saved")
        assert response.status_code == 200
        data = response.json()
        assert "saved_searches" in data
