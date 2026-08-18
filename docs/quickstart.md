# VisionAudioForge Quickstart

Get the platform running and make your first API calls in under 5 minutes.

## Prerequisites

- **Docker Compose v2.20+**. Earlier versions support neither `--wait` nor
  `env_file: required: false`, both of which this stack relies on.
- ~8 GB free disk. The backend image is 3.94 GB (torch, faiss, ffmpeg).
- `curl` or any HTTP client (Postman, httpie, etc.)

## 1. Start the Platform

```bash
git clone https://github.com/navigreen311/visionaudioforge.git && cd visionaudioforge
docker compose up -d --wait
```

That is the whole setup. **You do not need to create a `.env`** — every setting
has a development default in `docker-compose.yml`. Copy `.env.example` to
`.env` only to override something.

`--wait` blocks until every healthcheck passes and both one-shot jobs have
exited 0, and returns non-zero if they do not. Plain `up -d` returns as soon as
containers are *created*, which is well before anything is usable.

Nine services, seven long-running:

| Service | Where | Notes |
| --- | --- | --- |
| `nginx` | http://localhost | The front door: serves the console, proxies `/api` and `/ws` |
| `frontend` | http://localhost:3000 | Next.js console, direct (bypasses nginx) |
| `api` | http://localhost:8000 | FastAPI + Uvicorn |
| `db` | :5432 | `pgvector/pgvector:pg16` — the `vector` extension is required |
| `redis` | :6379 | Cache and Celery broker |
| `minio` | :9000, console :9001 | Object storage |
| `celery_worker` | — | Background tasks |
| `migrate` | — | One-shot: `alembic upgrade head`, then exits 0 |
| `minio_init` | — | One-shot: creates the bucket, then exits 0 |

Migrations and bucket creation run automatically on every `up` and are both
idempotent. `api` does not start until they have succeeded, so a failed
migration fails the boot rather than producing a half-working API.

### Ports already in use?

Every published port is overridable — this repo is often checked out several
times on one machine:

```bash
HTTP_PORT=8080 FRONTEND_PORT=3100 API_PORT=8001 docker compose up -d --wait
```

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

> **Every endpoint below needs that token.** The API is protected by app-level
> authentication middleware: anything not on the public allowlist answers 401
> without a `Authorization: Bearer` header, whether or not the route itself
> declares a dependency. Only `/api/health`, `/api/metrics`, the three
> `/api/auth` credential endpoints and the OpenAPI surface are open. See
> [auth.md](auth.md).

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
  -H "Authorization: Bearer $TOKEN" \
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
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.png"
```

## 6. Search Your Assets

Index an asset, then search by text:

```bash
# Index
curl -X POST http://localhost:8000/api/search/index \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"asset_id": "<your-asset-id>"}'

# Search
curl -X POST http://localhost:8000/api/search/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "person walking", "k": 5}'
```

## Verify the whole stack

The commands above exercise one path at a time. To assert the entire stack —
migrations at head, both Postgres extensions, the bucket, the auth boundary,
the console through nginx, the WebSocket upgrade, and the Celery worker taking
a real task off the queue:

```bash
make smoke          # full stack
make smoke-core     # api + db + redis + minio, no frontend/nginx
```

This is exactly what the `compose-smoke` job runs in CI, so a green run locally
means a green run there.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `env file .env not found` | Compose older than v2.20 — `required: false` is unsupported. Upgrade, or `cp .env.example .env`. |
| `bind: address already in use` | Something else holds :80, :3000 or :8000. Set `HTTP_PORT`, `FRONTEND_PORT`, `API_PORT`. |
| `/bin/sh^M: bad interpreter` | Scripts checked out with CRLF. `.gitattributes` prevents this; re-clone or `git add --renormalize .`. |
| API 401s on everything | Expected. Everything except the allowlist needs a Bearer token — see [auth.md](auth.md). |
| Console blank through :80, fine on :3000 | A Content-Security-Policy blocking Next's inline scripts. Check the `script-src` in `nginx/nginx.conf`. |
| `migrate` exits non-zero | Read `docker compose logs migrate`. The API deliberately will not start on a failed migration. |

## Next Steps

- Browse all 321 endpoints in the [API Reference](api-reference.md)
- Open the interactive Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs)
- Create a dataset: `POST /api/datasets`
- Build a pipeline: `POST /api/pipeline/create`
- Set up alerts: `POST /api/alerts/rules`
- Connect integrations: `POST /api/integrations/slack/send`
