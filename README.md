# VisionAudioForge

AI-powered vision and audio analysis platform for capture, processing, training, and deployment of computer vision and audio ML models.

## Tech Stack

- **Backend**: Python 3.11 / FastAPI / Pydantic v2 / Uvicorn / Celery
- **Frontend**: Next.js 14 / TypeScript / Tailwind CSS / React 18 / Zustand / React Query
- **Database**: PostgreSQL 16 + pgvector / Redis 7
- **AI/ML**: PyTorch, OpenCV, Librosa, FAISS, HuggingFace Transformers, CLIP
- **Storage**: MinIO (S3-compatible)
- **Infra**: Docker Compose, NGINX reverse proxy
- **Auth**: JWT / OAuth2

## Quick Start

```bash
# 1. Clone and setup
git clone <repo-url>
cd vision-audio-ai
cp .env.example .env

# 2. Start all services
docker compose up --build

# 3. Access
# Frontend:  http://localhost:3000
# API:       http://localhost:8000
# API Docs:  http://localhost:8000/docs
# MinIO:     http://localhost:9001
```

Or use the Makefile:

```bash
make dev     # docker compose up
make build   # docker compose build
make test    # run tests
make lint    # run linters
```

## Modules (V1 Status)

| Module       | Backend Route          | Frontend Page    | Status          |
|-------------|------------------------|------------------|-----------------|
| Auth        | /api/auth/*            | -                | Stub            |
| Vision      | /api/vision/*          | /vision          | Stub            |
| Audio       | /api/audio/*           | /audio           | Stub            |
| Transfer    | /api/transfer/*        | /transform       | Stub            |
| Experiments | /api/experiments       | /train           | Stub            |
| Registry    | /api/registry/*        | /evaluation      | Stub            |
| Search      | /api/search/*          | /search          | Stub            |
| Pipeline    | /api/pipeline/*        | /pipeline        | Stub            |
| Alerts      | /api/alerts/*          | /alerts          | Stub            |
| Agents      | /api/agents/*          | /agents          | Stub            |
| Assets      | /api/assets/*          | /assets          | Stub            |
| Datasets    | /api/datasets          | /capture         | Stub            |
| Safety      | /api/safety/*          | -                | Stub            |
| Workspaces  | /api/workspaces        | /settings        | Stub            |
| Validate    | -                      | /validate        | Stub            |
| Investigate | -                      | /investigate     | Stub            |

## Architecture

```
nginx (port 80) -> / -> frontend:3000
                -> /api -> api:8000
                -> /ws  -> api:8000 (WebSocket)

api -> PostgreSQL (pgvector)
    -> Redis (cache + Celery broker)
    -> MinIO (object storage)
    -> Celery workers (async tasks)
```

## Development

- Backend code: `backend/`
- Frontend code: `frontend/`
- Database migrations: `backend/alembic/`
- Docker configs: `docker-compose.yml`, `nginx/nginx.conf`
