"""Search API routes — wired to CLIP EmbeddingService + FAISSIndexService."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from app.services.search.embeddings import EmbeddingService
from app.services.search.faiss_index import FAISSIndexService
from app.services.search.search_service import CrossModalSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------

_embedding_svc: EmbeddingService | None = None
_index_svc: FAISSIndexService | None = None
_search_svc: CrossModalSearchService | None = None


def _get_embedding_service() -> EmbeddingService:
    global _embedding_svc
    if _embedding_svc is None:
        _embedding_svc = EmbeddingService()
    return _embedding_svc


def _get_index_service() -> FAISSIndexService:
    global _index_svc
    if _index_svc is None:
        _index_svc = FAISSIndexService(dimension=512)
        _index_svc.create_index("flat")
    return _index_svc


def _get_search_service() -> CrossModalSearchService:
    global _search_svc
    if _search_svc is None:
        _search_svc = CrossModalSearchService(
            embedding_svc=_get_embedding_service(),
            index_svc=_get_index_service(),
            db_session=None,
        )
    return _search_svc


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class SearchQueryRequest(BaseModel):
    query: str
    modality: str = Field(default="text", pattern="^(text|image)$")
    k: int = Field(default=10, ge=1, le=100)
    filters: dict[str, Any] = Field(default_factory=dict)


class IndexAssetRequest(BaseModel):
    asset_id: str


class SearchResultItem(BaseModel):
    asset_id: str
    score: float
    rank: int
    asset_type: str = "unknown"
    filename: str = ""


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total_results: int
    processing_time_ms: float


class IndexResponse(BaseModel):
    asset_id: str
    indexed: bool
    embedding_dim: int = 512


class StatsResponse(BaseModel):
    total_vectors: int
    dimension: int
    index_type: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/query", response_model=SearchResponse)
async def search_query(body: SearchQueryRequest):
    """Search by text query or image modality.

    For text queries, the query string is embedded via CLIP and searched
    against the FAISS index.  Image queries should use ``/query`` with a
    file upload (multipart) — see ``search_query_image``.
    """
    t0 = time.perf_counter()

    try:
        search_svc = _get_search_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if body.modality == "image":
        raise HTTPException(
            status_code=400,
            detail="Image search requires file upload. Use multipart/form-data with an 'file' field.",
        )

    # Text search
    try:
        raw_results = await search_svc.search_by_text(
            query=body.query,
            k=body.k,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    elapsed_ms = (time.perf_counter() - t0) * 1000

    results = [
        SearchResultItem(
            asset_id=r["asset_id"],
            score=r["score"],
            rank=r["rank"],
            asset_type=r.get("asset_type", "unknown"),
            filename=r.get("filename", ""),
        )
        for r in raw_results
    ]

    return SearchResponse(
        results=results,
        total_results=len(results),
        processing_time_ms=round(elapsed_ms, 2),
    )


@router.post("/query/upload", response_model=SearchResponse)
async def search_query_image(file: UploadFile = File(...), k: int = 10):
    """Search by image upload — embed the image and find similar assets."""
    t0 = time.perf_counter()

    try:
        search_svc = _get_search_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    image_data = await file.read()
    if not image_data:
        raise HTTPException(status_code=400, detail="Empty file upload")

    try:
        raw_results = await search_svc.search_by_image(image_data, k=k)
    except Exception as exc:
        logger.exception("Image search failed")
        raise HTTPException(status_code=500, detail=f"Image search failed: {exc}") from exc

    elapsed_ms = (time.perf_counter() - t0) * 1000

    results = [
        SearchResultItem(
            asset_id=r["asset_id"],
            score=r["score"],
            rank=r["rank"],
            asset_type=r.get("asset_type", "unknown"),
            filename=r.get("filename", ""),
        )
        for r in raw_results
    ]

    return SearchResponse(
        results=results,
        total_results=len(results),
        processing_time_ms=round(elapsed_ms, 2),
    )


@router.post("/index", response_model=IndexResponse)
async def index_asset(body: IndexAssetRequest):
    """Generate an embedding for an asset and add it to the FAISS index.

    In a full implementation this would load the asset from the DB and
    download the file from storage.  Currently it generates a placeholder
    embedding so the wiring can be validated end-to-end.
    """
    try:
        search_svc = _get_search_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Validate asset_id is a valid UUID
    try:
        UUID(body.asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid asset_id — expected UUID format") from exc

    # In production: load asset from DB, download file bytes from storage.
    # For now, generate a placeholder embedding so the index wiring works.
    try:
        embedding_svc = _get_embedding_service()
        # Generate a deterministic-ish embedding from the asset_id text
        vector = embedding_svc.embed_text(body.asset_id)
        index_svc = _get_index_service()
        index_svc.add_vectors(vector.reshape(1, -1), [body.asset_id])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return IndexResponse(
        asset_id=body.asset_id,
        indexed=True,
        embedding_dim=512,
    )


@router.get("/stats", response_model=StatsResponse)
async def search_stats():
    """Return FAISS index statistics."""
    try:
        index_svc = _get_index_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    stats = index_svc.get_stats()
    return StatsResponse(
        total_vectors=stats["total_vectors"],
        dimension=stats["dimension"],
        index_type=stats["index_type"],
    )


@router.post("/similar/{asset_id}", response_model=SearchResponse)
async def similar_assets(asset_id: str, k: int = 10):
    """Find assets similar to an already-indexed asset."""
    t0 = time.perf_counter()

    try:
        search_svc = _get_search_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Validate UUID
    try:
        UUID(asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid asset_id — expected UUID format") from exc

    # Check if asset is in the index
    found = any(aid == asset_id for aid in _get_index_service().id_map.values())
    if not found:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found in search index")

    try:
        raw_results = await search_svc.search_similar(asset_id, k=k)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    elapsed_ms = (time.perf_counter() - t0) * 1000

    results = [
        SearchResultItem(
            asset_id=r["asset_id"],
            score=r["score"],
            rank=r["rank"],
            asset_type=r.get("asset_type", "unknown"),
            filename=r.get("filename", ""),
        )
        for r in raw_results
    ]

    return SearchResponse(
        results=results,
        total_results=len(results),
        processing_time_ms=round(elapsed_ms, 2),
    )
