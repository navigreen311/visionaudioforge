"""Search API routes — cross-modal search with CLIP + FAISS."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.services.search.embeddings import EmbeddingService
from app.services.search.faiss_index import FAISSIndexService
from app.services.search.search_service import CrossModalSearchService

router = APIRouter(prefix="/api/search", tags=["search"])

# ---------------------------------------------------------------------------
# Singleton services (created lazily at module level for the API layer)
# ---------------------------------------------------------------------------
_embedding_svc = EmbeddingService()
_index_svc = FAISSIndexService(dimension=512)
_search_svc = CrossModalSearchService(_embedding_svc, _index_svc)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class TextSearchRequest(BaseModel):
    query: str
    modality: str = "text"
    k: int = 10
    modality_filter: Optional[str] = None


class IndexRequest(BaseModel):
    asset_id: str


class SearchResponse(BaseModel):
    results: list[dict]
    query_type: str
    total_results: int
    processing_time_ms: float


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/query", response_model=SearchResponse)
async def search_query(
    # Text mode fields (JSON body)
    body: Optional[TextSearchRequest] = None,
    # Image mode fields (multipart)
    file: Optional[UploadFile] = File(None),
    modality: Optional[str] = Form(None),
    k: Optional[int] = Form(None),
):
    """Perform a cross-modal search.

    **Text mode** — send JSON body::

        {"query": "dog playing in park", "modality": "text", "k": 10}

    **Image mode** — send multipart form with ``file``, ``modality=image``, ``k=10``.
    """
    t0 = time.perf_counter()

    # Determine search mode
    if file is not None and modality == "image":
        image_bytes = await file.read()
        search_k = k or 10
        results = await _search_svc.search_by_image(image_bytes, k=search_k)
        query_type = "image"
    elif body is not None:
        results = await _search_svc.search_by_text(
            body.query, k=body.k, modality_filter=body.modality_filter
        )
        query_type = "text"
    else:
        return JSONResponse(
            status_code=400,
            content={"detail": "Provide either a JSON body with 'query' or a multipart file upload with modality=image."},
        )

    elapsed = (time.perf_counter() - t0) * 1000

    return SearchResponse(
        results=results,
        query_type=query_type,
        total_results=len(results),
        processing_time_ms=round(elapsed, 2),
    )


@router.post("/index")
async def index_asset(body: IndexRequest):
    """Index a single asset by its ID.

    In a full implementation this would fetch the asset file from storage,
    determine its modality, and pass it through the embedding pipeline.
    For now, returns a placeholder response indicating the endpoint is wired up.
    """
    return {
        "asset_id": body.asset_id,
        "embedded": False,
        "detail": "Asset indexing requires file storage integration. Endpoint is wired and ready.",
    }


@router.get("/stats")
async def search_stats():
    """Return FAISS index statistics."""
    stats = _index_svc.get_stats()
    return stats
