"""Search API routes — wired to CLIP EmbeddingService + FAISSIndexService."""

from __future__ import annotations

import io
import logging
import time
from typing import Any
from uuid import UUID

import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from app.services.search.embeddings import EmbeddingService
from app.services.search.faiss_index import FAISSIndexService
from app.services.search.search_service import CrossModalSearchService
from app.services.search.fusion import EventFusionEngine
from app.services.search.saved_searches import SavedSearchService
from app.services.search.conversational import ConversationalSearch
from app.services.search.voice_query import VoiceQueryService

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
    query: str = ""
    modality: str = Field(default="text", pattern="^(text|image|audio)$")
    k: int = Field(default=10, ge=1, le=100)
    filters: dict[str, Any] = Field(default_factory=dict)
    query_image_b64: str | None = None
    query_audio_b64: str | None = None


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


class FuseRequest(BaseModel):
    workspace_id: str
    start: str
    end: str


class SaveSearchRequest(BaseModel):
    workspace_id: str = "00000000-0000-0000-0000-000000000000"
    user_id: str = "default"
    name: str
    query: str
    modality: str = "text"
    filters: dict[str, Any] = Field(default_factory=dict)


class ConversationalRequest(BaseModel):
    query: str
    history: list[str] = Field(default_factory=list)
    workspace_id: str = "00000000-0000-0000-0000-000000000000"


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

    # Image search via base64 payload
    if body.query_image_b64:
        try:
            import base64 as b64mod
            image_data = b64mod.b64decode(body.query_image_b64)
            raw_results = await search_svc.search_by_image(image_data, k=body.k)
        except Exception as exc:
            logger.exception("Image b64 search failed")
            raise HTTPException(status_code=500, detail=f"Image search failed: {exc}") from exc
    # Audio search via base64 payload
    elif body.query_audio_b64:
        try:
            import base64 as b64mod
            audio_data = b64mod.b64decode(body.query_audio_b64)
            audio_array, sr = _decode_audio(audio_data)
            embedding_svc = _get_embedding_service()
            index_svc = _get_index_service()
            vector = embedding_svc.embed_audio(audio_array, sr)
            raw_results = index_svc.search(vector, k=body.k)
        except Exception as exc:
            logger.exception("Audio b64 search failed")
            raise HTTPException(status_code=500, detail=f"Audio search failed: {exc}") from exc
    elif body.modality == "image":
        raise HTTPException(
            status_code=400,
            detail="Image search requires file upload or query_image_b64 field.",
        )
    else:
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


@router.get("/index-status")
async def search_index_status():
    """Return per-modality index counts for the frontend dashboard."""
    try:
        index_svc = _get_index_service()
        total = index_svc.get_stats().get("total_vectors", 0)
    except Exception:
        total = 0
    return {
        "images": 0,
        "audio": 0,
        "videos": 0,
        "total": total,
    }


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


# ---------------------------------------------------------------------------
# Audio / CLAP search
# ---------------------------------------------------------------------------


@router.post("/audio-query")
async def search_audio_query(file: UploadFile = File(...), k: int = 10):
    """Search by audio upload — embed with CLAP and find similar assets."""
    t0 = time.perf_counter()

    audio_data = await file.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        embedding_svc = _get_embedding_service()
        index_svc = _get_index_service()

        # Decode audio bytes
        audio_array, sr = _decode_audio(audio_data)
        vector = embedding_svc.embed_audio(audio_array, sr)

        raw_results = index_svc.search(vector, k=k)
    except Exception as exc:
        logger.exception("Audio query search failed")
        raise HTTPException(status_code=500, detail=f"Audio search failed: {exc}") from exc

    elapsed_ms = (time.perf_counter() - t0) * 1000

    results = [
        SearchResultItem(
            asset_id=r["asset_id"],
            score=r["score"],
            rank=r["rank"],
        )
        for r in raw_results
    ]

    return SearchResponse(
        results=results,
        total_results=len(results),
        processing_time_ms=round(elapsed_ms, 2),
    )


# ---------------------------------------------------------------------------
# Voice query (STT -> text search)
# ---------------------------------------------------------------------------


@router.post("/voice")
async def search_voice(file: UploadFile = File(...)):
    """Transcribe voice recording and run a text search."""
    audio_data = await file.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        audio_array, sr = _decode_audio(audio_data)
        voice_svc = VoiceQueryService()
        result = await voice_svc.process_voice_query(audio_array, sr)
    except Exception as exc:
        logger.exception("Voice query failed")
        raise HTTPException(status_code=500, detail=f"Voice query failed: {exc}") from exc

    return JSONResponse(content={
        "transcript": result["transcript"],
        "search_results": result["search_results"],
    })


# ---------------------------------------------------------------------------
# Event fusion / timeline
# ---------------------------------------------------------------------------


@router.post("/fuse")
async def search_fuse(body: FuseRequest):
    """Build a fused multimodal timeline for a time range."""
    fusion = EventFusionEngine()

    try:
        timeline = await fusion.build_multimodal_timeline(
            db=None,
            workspace_id=body.workspace_id,
            start=body.start,
            end=body.end,
        )
    except Exception as exc:
        logger.exception("Fusion timeline failed")
        raise HTTPException(status_code=500, detail=f"Fusion failed: {exc}") from exc

    return JSONResponse(content={"timeline": timeline})


# ---------------------------------------------------------------------------
# Saved searches
# ---------------------------------------------------------------------------


@router.post("/saved")
async def save_search(body: SaveSearchRequest):
    """Save a search for later re-execution."""
    svc = SavedSearchService()
    result = await svc.save_search(
        db=None,
        workspace_id=body.workspace_id,
        user_id=body.user_id,
        name=body.name,
        query=body.query,
        modality=body.modality,
        filters=body.filters,
    )
    return JSONResponse(content=result)


@router.get("/saved")
async def list_saved_searches(
    workspace_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    user_id: str | None = Query(default=None),
):
    """List saved searches for a workspace."""
    svc = SavedSearchService()
    results = await svc.list_saved_searches(
        db=None,
        workspace_id=workspace_id,
        user_id=user_id,
    )
    return JSONResponse(content={"saved_searches": results})


@router.post("/saved/{search_id}/execute")
async def execute_saved_search(search_id: str):
    """Re-run a saved search by ID."""
    svc = SavedSearchService()
    results = await svc.execute_saved_search(db=None, search_id=search_id)
    return JSONResponse(content={"results": results})


# ---------------------------------------------------------------------------
# Conversational search
# ---------------------------------------------------------------------------


@router.post("/conversational")
async def conversational_search(body: ConversationalRequest):
    """Context-aware conversational search with follow-up suggestions."""
    svc = ConversationalSearch()
    result = await svc.search_with_context(
        query=body.query,
        conversation_history=body.history,
        workspace_id=body.workspace_id,
    )
    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# Audio decoding helper
# ---------------------------------------------------------------------------


def _decode_audio(data: bytes) -> tuple[np.ndarray, int]:
    """Decode audio bytes to numpy array and sample rate."""
    try:
        import soundfile as sf

        audio_array, sr = sf.read(io.BytesIO(data))
        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)
        return audio_array.astype(np.float32), sr
    except ImportError:
        logger.warning("soundfile not available — generating placeholder audio")
        return np.random.randn(16000).astype(np.float32), 16000
