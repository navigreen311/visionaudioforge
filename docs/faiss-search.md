# FAISS Cross-Modal Search (M13)

## Overview

Cross-modal search enables finding assets (images, audio, video) using natural language queries or visual similarity. It uses OpenAI's CLIP model to project both text and images into a shared 512-dimensional embedding space, then uses FAISS for fast nearest-neighbour retrieval.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  API Routes  │────▶│ CrossModalSearch  │────▶│ EmbeddingService│
│  /api/search │     │    Service        │     │ (CLIP model)    │
└──────────────┘     └────────┬─────────┘     └─────────────────┘
                              │
                     ┌────────▼─────────┐
                     │ FAISSIndexService │
                     │ (vector index)   │
                     └──────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `EmbeddingService` | `backend/app/services/search/embeddings.py` | CLIP-based embedding generation for images and text |
| `FAISSIndexService` | `backend/app/services/search/faiss_index.py` | FAISS vector index management (add, search, persist) |
| `CrossModalSearchService` | `backend/app/services/search/search_service.py` | Orchestrates embedding + indexing + DB metadata |
| API Routes | `backend/app/api/routes/search.py` | REST endpoints for search, indexing, stats |
| Search Page | `frontend/src/app/(dashboard)/search/page.tsx` | UI with modality toggle, upload, results grid |

## API Endpoints

### `POST /api/search/query`

**Text search** (JSON body):
```json
{
  "query": "dog playing in park",
  "modality": "text",
  "k": 10
}
```

**Image search** (multipart form):
- `file`: image file upload
- `modality`: `"image"`
- `k`: number of results (default 10)

**Response**:
```json
{
  "results": [
    {
      "asset_id": "uuid",
      "score": 0.85,
      "rank": 1,
      "asset_type": "image",
      "filename": "photo.jpg",
      "path": "/assets/photo.jpg"
    }
  ],
  "query_type": "text",
  "total_results": 10,
  "processing_time_ms": 42.5
}
```

### `POST /api/search/index`

Index a single asset by ID.
```json
{"asset_id": "uuid-string"}
```

### `GET /api/search/stats`

Returns FAISS index statistics:
```json
{
  "total_vectors": 1500,
  "dimension": 512,
  "index_type": "flat",
  "is_trained": true
}
```

## Embedding Model

- **Model**: `openai/clip-vit-base-patch32` (from Hugging Face `transformers`)
- **Dimension**: 512
- **Normalization**: L2-normalized (unit vectors) for cosine similarity via inner product
- **Fallback**: Random embeddings when `transformers` is not installed (logged as warning)

## FAISS Index Types

| Type | Class | Use Case |
|------|-------|----------|
| `flat` | `IndexFlatIP` | Exact search, best for < 100K vectors |
| `ivf` | `IndexIVFFlat` | Approximate search with 100 clusters, better for large indexes |

Both use inner product metric (equivalent to cosine similarity on normalized vectors).

## Environment Variables

No additional env vars required. The search service uses the existing `TORCH_DEVICE` setting from `app/config.py`.

## Running Tests

```bash
cd backend
python -m pytest tests/test_faiss_search.py -v
```

## Dependencies

Already included in `backend/requirements.txt`:
- `faiss-cpu==1.7.4`
- `transformers==4.37.2`
- `torch==2.2.0`
- `Pillow==10.2.0`
- `numpy==1.26.4`
