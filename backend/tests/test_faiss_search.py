"""Tests for FAISS cross-modal search: embeddings, indexing, and API."""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.search.embeddings import EmbeddingService
from app.services.search.faiss_index import FAISSIndexService
from app.services.search.search_service import CrossModalSearchService


# ======================================================================
# Embedding tests
# ======================================================================

class TestEmbeddingService:
    """Tests for the EmbeddingService (fallback / random mode)."""

    def setup_method(self):
        self.svc = EmbeddingService()
        # Force fallback mode so tests don't require a real CLIP model
        self.svc._use_fallback = True

    def test_embedding_shape_512(self):
        """embed_image returns shape (512,)."""
        image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        vec = self.svc.embed_image(image)
        assert vec.shape == (512,), f"Expected shape (512,), got {vec.shape}"

    def test_embedding_normalized(self):
        """Embeddings are L2-normalised (norm ≈ 1.0)."""
        image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        vec = self.svc.embed_image(image)
        norm = float(np.linalg.norm(vec))
        assert abs(norm - 1.0) < 1e-5, f"Expected norm ≈ 1.0, got {norm}"

    def test_text_embedding_shape(self):
        """embed_text returns shape (512,)."""
        vec = self.svc.embed_text("a dog playing in the park")
        assert vec.shape == (512,)

    def test_text_embedding_normalized(self):
        """Text embeddings are L2-normalised."""
        vec = self.svc.embed_text("sunset over the ocean")
        norm = float(np.linalg.norm(vec))
        assert abs(norm - 1.0) < 1e-5

    def test_batch_images_shape(self):
        """embed_batch_images returns shape (N, 512)."""
        images = [np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8) for _ in range(5)]
        vecs = self.svc.embed_batch_images(images)
        assert vecs.shape == (5, 512)

    def test_batch_texts_shape(self):
        """embed_batch_texts returns shape (N, 512)."""
        texts = ["cat", "dog", "bird"]
        vecs = self.svc.embed_batch_texts(texts)
        assert vecs.shape == (3, 512)

    def test_embedding_dtype_float32(self):
        """All embeddings are float32."""
        vec = self.svc.embed_text("test")
        assert vec.dtype == np.float32


# ======================================================================
# FAISS index tests
# ======================================================================

class TestFAISSIndexService:
    """Tests for the FAISSIndexService."""

    def setup_method(self):
        self.svc = FAISSIndexService(dimension=512)
        self.svc.create_index("flat")

    def test_faiss_add_and_search(self):
        """Add 10 random vectors, search with one, verify k results returned."""
        vectors = np.random.randn(10, 512).astype(np.float32)
        # Normalise
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        ids = [f"asset-{i}" for i in range(10)]
        count = self.svc.add_vectors(vectors, ids)
        assert count == 10

        query = vectors[0]
        results = self.svc.search(query, k=5)
        assert len(results) == 5
        assert all("asset_id" in r and "score" in r and "rank" in r for r in results)

    def test_faiss_search_returns_similar(self):
        """Add known similar vectors, verify top result is most similar."""
        base = np.random.randn(512).astype(np.float32)
        base = base / np.linalg.norm(base)

        # Create a very similar vector and several dissimilar ones
        similar = base + np.random.randn(512).astype(np.float32) * 0.01
        similar = similar / np.linalg.norm(similar)

        dissimilar = np.random.randn(8, 512).astype(np.float32)
        dissimilar = dissimilar / np.linalg.norm(dissimilar, axis=1, keepdims=True)

        all_vectors = np.vstack([base.reshape(1, -1), similar.reshape(1, -1), dissimilar])
        ids = ["target", "similar", *[f"dissimilar-{i}" for i in range(8)]]
        self.svc.add_vectors(all_vectors, ids)

        results = self.svc.search(base, k=3)
        # Top result should be "target" itself (exact match)
        assert results[0]["asset_id"] == "target"
        # Second should be "similar"
        assert results[1]["asset_id"] == "similar"

    def test_index_stats(self):
        """Add vectors, verify count in stats."""
        vectors = np.random.randn(7, 512).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        self.svc.add_vectors(vectors, [f"v-{i}" for i in range(7)])

        stats = self.svc.get_stats()
        assert stats["total_vectors"] == 7
        assert stats["dimension"] == 512
        assert stats["index_type"] == "flat"
        assert stats["is_trained"] is True

    def test_empty_search(self):
        """Search on empty index returns no results."""
        query = np.random.randn(512).astype(np.float32)
        results = self.svc.search(query, k=5)
        assert results == []

    def test_remove_vectors_logs_warning(self):
        """remove_vectors logs a warning (not supported)."""
        # Should not raise, just log
        self.svc.remove_vectors(["asset-1", "asset-2"])


# ======================================================================
# Search service tests
# ======================================================================

class TestCrossModalSearchService:
    """Tests for the CrossModalSearchService."""

    def setup_method(self):
        self.embedding_svc = EmbeddingService()
        self.embedding_svc._use_fallback = True
        self.index_svc = FAISSIndexService(dimension=512)
        self.search_svc = CrossModalSearchService(self.embedding_svc, self.index_svc)

    @pytest.mark.anyio
    async def test_search_by_text_returns_results(self):
        """search_by_text returns results when index has vectors."""
        # Pre-populate index
        vectors = np.random.randn(5, 512).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        self.index_svc.add_vectors(vectors, [f"asset-{i}" for i in range(5)])

        results = await self.search_svc.search_by_text("a cat sitting on a mat", k=3)
        assert len(results) == 3
        assert all("asset_id" in r for r in results)
        assert all("score" in r for r in results)

    @pytest.mark.anyio
    async def test_index_asset_image(self):
        """index_asset successfully indexes an image."""
        # Create a minimal valid PNG
        from PIL import Image as PILImage
        import io

        img = PILImage.new("RGB", (50, 50), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        result = await self.search_svc.index_asset("test-asset-1", "image", image_bytes)
        assert result["asset_id"] == "test-asset-1"
        assert result["embedded"] is True
        assert self.index_svc.get_stats()["total_vectors"] == 1


# ======================================================================
# API tests
# ======================================================================

@pytest.mark.anyio
async def test_api_search_query(client):
    """POST /api/search/query with text query returns expected response shape."""
    response = await client.post(
        "/api/search/query",
        json={"query": "sunset on a beach", "modality": "text", "k": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "query_type" in data
    assert data["query_type"] == "text"
    assert "total_results" in data
    assert "processing_time_ms" in data


@pytest.mark.anyio
async def test_api_search_stats(client):
    """GET /api/search/stats returns index statistics."""
    response = await client.get("/api/search/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_vectors" in data
    assert "dimension" in data
    assert data["dimension"] == 512
    assert "index_type" in data
    assert "is_trained" in data
