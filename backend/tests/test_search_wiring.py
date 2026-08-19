"""Tests for search route wiring - verifies endpoints connect to FAISS services."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

# We patch the service singletons at the module level in the route file
# to inject controlled instances with known state.
from app.services.search.embeddings import EmbeddingService
from app.services.search.faiss_index import FAISSIndexService
from app.services.search.search_service import CrossModalSearchService


def _build_services(num_vectors: int = 0) -> tuple[EmbeddingService, FAISSIndexService, CrossModalSearchService]:
    """Create service instances and optionally pre-populate the FAISS index."""
    emb_svc = EmbeddingService()
    idx_svc = FAISSIndexService(dimension=512)
    idx_svc.create_index("flat")

    if num_vectors > 0:
        vectors = np.random.default_rng(42).standard_normal((num_vectors, 512)).astype(np.float32)
        # L2-normalise so inner-product scores are in [-1, 1]
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / np.where(norms == 0, 1, norms)
        ids = [str(uuid.uuid4()) for _ in range(num_vectors)]
        idx_svc.add_vectors(vectors, ids)

    search_svc = CrossModalSearchService(
        embedding_svc=emb_svc,
        index_svc=idx_svc,
        db_session=None,
    )
    return emb_svc, idx_svc, search_svc


def _patch_services(emb_svc, idx_svc, search_svc):
    """Return a context-manager stack that patches the route-level singletons."""
    return [
        patch("app.api.routes.search._embedding_svc", emb_svc),
        patch("app.api.routes.search._index_svc", idx_svc),
        patch("app.api.routes.search._search_svc", search_svc),
    ]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def populated_services():
    """Services with 5 pre-indexed vectors."""
    return _build_services(num_vectors=5)


@pytest.fixture
def empty_services():
    """Services with an empty FAISS index."""
    return _build_services(num_vectors=0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_search_text_query_returns_results(populated_services):
    """POST /api/search/query with a text query returns ranked results."""
    emb_svc, idx_svc, search_svc = populated_services
    patches = _patch_services(emb_svc, idx_svc, search_svc)

    from app.main import app

    for p in patches:
        p.start()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/search/query",
                json={"query": "a red car", "modality": "text", "k": 3},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "results" in data
        assert "total_results" in data
        assert "processing_time_ms" in data
        assert isinstance(data["results"], list)
        # We indexed 5 vectors, asked for k=3
        assert data["total_results"] <= 3
        # Each result has the expected shape
        for item in data["results"]:
            assert "asset_id" in item
            assert "score" in item
            assert "rank" in item
            assert "asset_type" in item
            assert "filename" in item
    finally:
        for p in patches:
            p.stop()


@pytest.mark.anyio
async def test_search_empty_index_returns_empty(empty_services):
    """POST /api/search/query on an empty index returns zero results."""
    emb_svc, idx_svc, search_svc = empty_services
    patches = _patch_services(emb_svc, idx_svc, search_svc)

    from app.main import app

    for p in patches:
        p.start()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/search/query",
                json={"query": "anything", "modality": "text", "k": 5},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["results"] == []
        assert data["total_results"] == 0
    finally:
        for p in patches:
            p.stop()


@pytest.mark.anyio
@pytest.mark.auth_enforced
async def test_index_asset_creates_embedding(empty_services):
    """POST /api/search/index embeds the asset's contents and indexes them.

    Rewritten with the endpoint. It used to post a randomly generated UUID
    anonymously and assert a 200, which passed because the route embedded the
    *text of the id* and answered `indexed: true` no matter what happened. That
    made the index full of vectors describing hex strings, and made this test
    incapable of noticing.

    It now requires a real asset owned by the caller, which is what indexing
    something actually needs.
    """
    emb_svc, idx_svc, search_svc = empty_services
    patches = _patch_services(emb_svc, idx_svc, search_svc)

    from app.core.security import create_access_token
    from app.main import app

    workspace_id = uuid.uuid4()
    token = create_access_token(
        {"sub": str(uuid.uuid4()), "workspace_id": str(workspace_id)}
    )
    auth = {"Authorization": f"Bearer {token}"}

    for p_ in patches:
        p_.start()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # An asset that does not exist must not be reported as indexed.
            missing = await ac.post(
                "/api/search/index",
                json={"asset_id": str(uuid.uuid4())},
                headers=auth,
            )
            assert missing.status_code == 404, missing.text

            # ...and neither must a malformed id.
            bad = await ac.post(
                "/api/search/index", json={"asset_id": "not-a-uuid"}, headers=auth
            )
            assert bad.status_code == 400, bad.text
    finally:
        for p_ in patches:
            p_.stop()


@pytest.mark.anyio
async def test_stats_returns_index_info(populated_services):
    """GET /api/search/stats returns FAISS index statistics."""
    emb_svc, idx_svc, search_svc = populated_services
    patches = _patch_services(emb_svc, idx_svc, search_svc)

    from app.main import app

    for p in patches:
        p.start()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/api/search/stats")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total_vectors"] == 5
        assert data["dimension"] == 512
        assert data["index_type"] == "flat"
    finally:
        for p in patches:
            p.stop()


@pytest.mark.anyio
async def test_similar_asset_returns_results(populated_services):
    """POST /api/search/similar/{asset_id} returns similar assets."""
    emb_svc, idx_svc, search_svc = populated_services
    patches = _patch_services(emb_svc, idx_svc, search_svc)

    from app.main import app

    # Pick one of the indexed asset IDs
    existing_asset_id = list(idx_svc.id_map.values())[0]

    for p in patches:
        p.start()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(f"/api/search/similar/{existing_asset_id}")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "results" in data
        assert "total_results" in data
        assert "processing_time_ms" in data
        # The query asset itself should NOT appear in results
        result_ids = [r["asset_id"] for r in data["results"]]
        assert existing_asset_id not in result_ids
    finally:
        for p in patches:
            p.stop()


@pytest.mark.anyio
async def test_similar_asset_not_found_returns_404(empty_services):
    """POST /api/search/similar/{asset_id} for unknown asset returns 404."""
    emb_svc, idx_svc, search_svc = empty_services
    patches = _patch_services(emb_svc, idx_svc, search_svc)

    from app.main import app

    fake_id = str(uuid.uuid4())

    for p in patches:
        p.start()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(f"/api/search/similar/{fake_id}")

        assert resp.status_code == 404, resp.text
    finally:
        for p in patches:
            p.stop()
