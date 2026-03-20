# VisionAudioForge Quickstart

Get the platform running and make your first API calls in under 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- `curl` or any HTTP client (Postman, httpie, etc.)

## 1. Start the Platform

```bash
git clone <repo-url> && cd vaf-p5-15-docs-api-complete
cp .env.example .env    # adjust if needed
docker compose up -d
```

Services launched:
- **API** at `http://localhost:8000` (FastAPI + Uvicorn)
- **Frontend** at `http://localhost:3000` (Next.js)
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **MinIO** on port 9000 (object storage)

Verify everything is healthy:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": {"status": "up", "latency_ms": 1.23},
    "redis": {"status": "up", "latency_ms": 0.45},
    "minio": {"status": "up", "latency_ms": null}
  },
  "uptime_seconds": 12.5,
  "timestamp": "2025-01-01T00:00:00+00:00"
}
```

## 2. Create a User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123",
    "workspace_name": "My Workspace"
  }'
```

Save the `access_token` from the response:

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "user": {
    "id": "...",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

```bash
export TOKEN="eyJhbGciOi..."
```

## 3. Upload an Image

```bash
curl -X POST http://localhost:8000/api/assets/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@photo.jpg" \
  -F "asset_type=image" \
  -F "workspace_id=<your-workspace-id>"
```

Response includes the `asset_id` you will use for analysis.

## 4. Run Object Detection

```bash
curl -X POST http://localhost:8000/api/vision/detect \
  -F "file=@photo.jpg" \
  -F "confidence=0.5"
```

Response:

```json
{
  "detections": [
    {
      "class_name": "person",
      "confidence": 0.92,
      "bbox": [100, 50, 300, 400]
    }
  ],
  "count": 1,
  "visualization": "<base64-png>",
  "processing_time_ms": 45.2
}
```

## 5. Run OCR

```bash
curl -X POST http://localhost:8000/api/vision/ocr \
  -F "file=@document.png"
```

## 6. Search Your Assets

Index an asset, then search by text:

```bash
# Index
curl -X POST http://localhost:8000/api/search/index \
  -H "Content-Type: application/json" \
  -d '{"asset_id": "<your-asset-id>"}'

# Search
curl -X POST http://localhost:8000/api/search/query \
  -H "Content-Type: application/json" \
  -d '{"query": "person walking", "k": 5}'
```

## Next Steps

- Browse all 321 endpoints in the [API Reference](api-reference.md)
- Open the interactive Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs)
- Create a dataset: `POST /api/datasets`
- Build a pipeline: `POST /api/pipeline/create`
- Set up alerts: `POST /api/alerts/rules`
- Connect integrations: `POST /api/integrations/slack/send`
