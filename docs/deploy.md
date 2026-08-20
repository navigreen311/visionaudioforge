# VAF Production Deployment Guide

## Prerequisites

- **Docker Engine** 24.0+ and **Docker Compose** v2.20+
- Minimum **4 GB RAM** available for containers (8 GB recommended)
- At least **20 GB** free disk space
- Linux host recommended (Ubuntu 22.04 LTS or later)

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with production values (strong passwords, real API keys)

# 2. Deploy
./scripts/deploy-prod.sh
```

## Production Deployment Steps

### 1. Configure Environment Variables

Copy `.env.example` to `.env` and set all values for production:

```bash
cp .env.example .env
```

**Critical settings to change:**
- `POSTGRES_PASSWORD` - use a strong, unique password
- `JWT_SECRET` - use a cryptographically random string (min 32 chars)
- `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` - change from defaults
- `ANTHROPIC_API_KEY` - set your real API key

### 2. Build and Start

```bash
# Build production images (no cache)
docker compose -f docker-compose.prod.yml build --no-cache

# Start all services
docker compose -f docker-compose.prod.yml up -d
```

### 3. Migrations

Nothing to do: the `migrate` service runs `alembic upgrade head` on every `up`
and `api` will not start until it exits 0. A failed migration fails the boot
rather than leaving a half-working API pointed at a stale schema.

To re-run them by hand after adding a revision:

```bash
docker compose run --rm migrate alembic upgrade head
```

### 4. Verify Deployment

Do not stop at `ps`. "Containers are running" was true of this stack for its
entire history while it was, in fact, unable to start at all.

```bash
make smoke        # boots and asserts the whole stack; exit status is the verdict
```

That checks migrations reached head, both Postgres extensions exist, the bucket
exists, `/api/health` reports every dependency up, the auth boundary answers 401
through nginx, the WebSocket upgrade is forwarded, and the Celery worker takes a
real task off the queue.

The manual equivalents:

```bash
docker compose ps                      # all healthy; migrate/minio_init exited 0
curl http://localhost:8000/api/health  # status healthy, db+redis+minio up
curl -I http://localhost/login         # console through nginx -> 200
curl -o /dev/null -w '%{http_code}\n' http://localhost/api/assets   # -> 401
```

A `401` there is the correct answer, not a fault — see [auth.md](auth.md).

## Environment Variables Reference

These are the names `Settings` in `backend/app/config.py` actually reads. It is
**case-sensitive and exact**: a plausible near-miss is silently ignored and the
application falls back to its default — which for `JWT_SECRET_KEY` means signing
tokens with a string published in this repository.

An earlier version of this table listed `DATABASE_URL`, `REDIS_URL`,
`JWT_SECRET` and `JWT_EXPIRE_MINUTES`. **Nothing reads any of those.** A
deployment configured from that table is running entirely on defaults.

| Variable | Description | Default | Required in prod |
|---|---|---|---|
| `POSTGRES_HOST` | Database host | `db` | No |
| `POSTGRES_PORT` | Database port | `5432` | No |
| `POSTGRES_USER` | Database user | `visionaudio` | Yes |
| `POSTGRES_PASSWORD` | Database password | `change-me-db-password` | **Yes** |
| `POSTGRES_DB` | Database name | `visionaudioforge` | Yes |
| `REDIS_HOST` | Redis host | `redis` | No |
| `REDIS_PORT` | Redis port | `6379` | No |
| `REDIS_PASSWORD` | Redis password | (empty) | Recommended |
| `MINIO_ENDPOINT` | MinIO S3 endpoint | `minio:9000` | No |
| `MINIO_ACCESS_KEY` | Credential the **application** uses | `minioaccess` | **Yes** |
| `MINIO_SECRET_KEY` | Credential the **application** uses | `miniosecret` | **Yes** |
| `MINIO_BUCKET` | Bucket name | `visionaudioforge` | Yes |
| `JWT_SECRET_KEY` | JWT signing secret — **not** `JWT_SECRET` | `change-me-jwt-secret` | **Yes** |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | No |
| `JWT_EXPIRATION_MINUTES` | Token expiry | `60` | No |
| `AUTH_REQUIRED` | App-level auth middleware | `true` | Leave `true` |
| `DEBUG_ERRORS` | Put exception text in 500 bodies | `false` | Leave `false` |
| `AUDIT_ENABLED` | Write an audit row per request | `true` | Yes |
| `CELERY_BROKER_URL` | Celery broker | `redis://redis:6379/0` | Yes |
| `CELERY_RESULT_BACKEND` | Celery results | `redis://redis:6379/1` | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key | (empty) | **No** — empty means the copilot runs in mock mode and the API still starts |
| `LOG_LEVEL` | Log level | `INFO` | No |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` | Yes |

`MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` configure the MinIO **server** and are
read by `docker-compose.yml`, not by the application. They must agree with
`MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`; compose wires them together for you.

The backend warns at startup if `JWT_SECRET_KEY` is still the default. Check
for it before declaring a deployment done:

```bash
docker compose logs api | grep -i "JWT_SECRET_KEY"
```

## Model Weights and Runtime Caches

The API image ships the CLIP weights inside it. That is a deliberate trade with
a real cost, so it is worth stating what was chosen and what it buys.

### Where the weights live

`backend/Dockerfile` bakes `openai/clip-vit-base-patch32` into the image at
build time, after the switch to `USER appuser`, into
`/home/appuser/.cache/huggingface/hub`. Nothing is fetched at request time.

Verify against a running stack — `HF_HUB_OFFLINE=1` is the point of the check,
because it proves the weights are present rather than merely reachable:

```bash
docker compose exec -T -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 api \
  python -c "from app.services.search.embeddings import EmbeddingService; \
print(EmbeddingService().embed_text('a photo of a cat').shape)"
# -> (512,)
```

### What it costs

| | Baked into the image (chosen) | Downloaded on first request | Named volume |
|---|---|---|---|
| Image size | **+609 MB** (11 GB -> 12 GB) | no change | no change |
| First search after deploy | served immediately | pays a ~600 MB download | pays it once per volume |
| Stack with no egress | works | **never works** | works after a seeded volume |
| Changing the model | rebuild + redeploy the image | no rebuild | re-seed the volume |
| Registry pull per node | +609 MB every deploy | — | — |

Measured, not estimated:

```bash
docker history --no-trunc --format '{{.Size}}\t{{.CreatedBy}}' vaf-backend:local | grep CLIP
# 609MB  RUN python -c "from transformers import CLIPModel, ...
```

The 609 MB is one copy of the weights, not two. `from_pretrained` caches both
`pytorch_model.bin` and `model.safetensors` — 578 MB each — when left to
choose, and only one is ever read, so the build passes `use_safetensors=True`.
Dropping that flag silently doubles this layer.

The deciding factor is the third row. An air-gapped or egress-filtered
deployment that downloads at first request does not degrade, it fails: the
first `POST /api/search/query` raises on a network call and every subsequent
one does the same. Paying 609 MB of registry transfer per deploy is the
cheaper failure mode than a search subsystem that cannot start.

A named volume avoids the per-deploy transfer and is the better answer at
double-digit node counts, where 609 MB per node per deploy stops being noise.
It costs a seeding step that must run before the first request, which is one
more thing that can be skipped — and skipping it fails exactly like the
download path. If you switch, seed it in the deploy job, not in an entrypoint.

**CLAP is not baked.** `laion/clap-htsat-unfused` is loaded lazily for audio
embeddings and is a further ~2 GB. It is left to download on first use, and
audio search therefore has the egress dependency described above. Bake it the
same way if audio search must work without egress — budget the image at ~14 GB
and re-check CI disk before you do.

### Runtime cache paths

The image runs as non-root `appuser`, so every library that wants to write a
cache needs somewhere to put it. `useradd --system` alone does not create a
home directory, and a library that falls back to a relative path lands in a
read-only `site-packages`. The Dockerfile therefore creates the home, owns it
by `appuser`, and sets each cache path explicitly rather than relying on
`$HOME` being inferred — `uvicorn` and the Celery worker are separate
entrypoints and must not disagree about where the cache is.

| Variable | Value | Used by |
|---|---|---|
| `HOME` | `/home/appuser` | fallback for everything below |
| `XDG_CACHE_HOME` | `/home/appuser/.cache` | generic cache root |
| `HF_HOME` | `/home/appuser/.cache/huggingface` | `huggingface_hub`, `transformers` |
| `HUGGINGFACE_HUB_CACHE` | `/home/appuser/.cache/huggingface/hub` | weight downloads |
| `NUMBA_CACHE_DIR` | `/home/appuser/.cache/numba` | `numba`, and so `librosa` |
| `MPLCONFIGDIR` | `/home/appuser/.cache/matplotlib` | `matplotlib` |

Without `HF_HOME` on a writable path, `huggingface_hub` raises
`PermissionError: [Errno 13] Permission denied: '/home/appuser'`, CLIP never
loads, and `POST /api/search/query` answers 500 — the whole text search
subsystem, while the container still reports healthy.

`NUMBA_CACHE_DIR` is defensive rather than a proven repair. The failure it
guards against —

```
cannot cache function '__o_fold': no locator available for file
'/usr/local/lib/python3.11/site-packages/librosa/core/notation.py'
```

— does not reproduce on the pinned `numba==0.67.0`; decoding with `HOME`,
`XDG_CACHE_HOME` and `NUMBA_CACHE_DIR` all unset was tested in this image and
succeeds, because numba now warns and compiles in memory instead of raising.
Setting it keeps numba off a read-only `site-packages` by construction, so a
future version that hard-errors cannot take audio decode down again, and it
recovers the cache hit that the in-memory fallback gives up on every start.

If you change any of these paths, change them in the `ENV` block and in the
`mkdir -p`/`chown` that follows it. A path that is set but not created and
owned fails the same way as one that was never set.

### What CI checks

`scripts/smoke-stack.sh` runs both subsystems against the built containers,
not against the runner. The `backend` job runs pytest on the runner and so
exercises code that never enters the image — neither failure above was ever
visible to it. The smoke job is what makes them visible:

```bash
./scripts/smoke-stack.sh          # full stack, 30 assertions
./scripts/smoke-stack.sh --core   # skip nginx and frontend, 24 assertions
```

It decodes a WAV through `POST /api/audio/analyze` and embeds a query through
`POST /api/search/query` from inside the `api` container, and separately
asserts that the CLIP weights are present and that `NUMBA_CACHE_DIR` is
writable. Breaking the cache configuration turns the run red rather than
leaving a healthy stack with two dead subsystems.

## Scaling Guide

### Horizontal Scaling

Scale individual services using Docker Compose replicas:

```bash
# Scale API to 4 instances
docker compose -f docker-compose.prod.yml up -d --scale api=4

# Scale Celery workers
docker compose -f docker-compose.prod.yml up -d --scale celery_worker=3
```

When scaling the API, update `nginx/nginx.conf` upstream to use Docker DNS:

```nginx
upstream api {
    server api:8000;
}
```

Docker Compose handles round-robin load balancing automatically when scaling.

### Vertical Scaling

Adjust resource limits in `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 4g    # Increase from 2g
      cpus: '2.0'   # Add CPU limit
```

## Backup Guide

### PostgreSQL Backup

```bash
# Create a database dump
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U vaf -Fc vaf > backup_$(date +%Y%m%d_%H%M%S).dump

# Restore from backup
docker compose -f docker-compose.prod.yml exec -T db \
  pg_restore -U vaf -d vaf --clean < backup.dump
```

### Redis Backup

```bash
# Trigger background save
docker compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE

# Copy RDB file
docker cp $(docker compose -f docker-compose.prod.yml ps -q redis):/data/dump.rdb ./redis_backup.rdb
```

### MinIO Backup

```bash
# Install mc (MinIO Client) if not present
# https://min.io/docs/minio/linux/reference/minio-mc.html

# Configure alias
mc alias set vaf http://localhost:9000 minioadmin minioadmin

# Mirror bucket to local directory
mc mirror vaf/vaf-assets ./minio_backup/

# Mirror to another S3-compatible target
mc mirror vaf/vaf-assets s3/backup-bucket/
```

### Automated Backups

Add a cron job for daily backups:

```bash
# crontab -e
0 2 * * * /path/to/project/scripts/backup.sh >> /var/log/vaf-backup.log 2>&1
```

## Monitoring Guide

### Health Check Endpoints

- **API**: `http://localhost:8000/api/health`
- **Frontend**: `http://localhost:3000`
- **MinIO**: `http://localhost:9000/minio/health/live`

### Docker Health Status

```bash
# Check all service health
docker compose -f docker-compose.prod.yml ps

# View logs for a specific service
docker compose -f docker-compose.prod.yml logs -f api

# View all logs
docker compose -f docker-compose.prod.yml logs -f --tail 100
```

### Prometheus Setup

Add a Prometheus service to `docker-compose.prod.yml`:

```yaml
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - prometheus_data:/prometheus
  restart: unless-stopped
  networks:
    - backend-net
```

Create `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vaf-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

### Grafana Setup

Add Grafana to `docker-compose.prod.yml`:

```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3001:3000"
  environment:
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
  volumes:
    - grafana_data:/var/lib/grafana
  depends_on:
    - prometheus
  restart: unless-stopped
  networks:
    - backend-net
```

Access Grafana at `http://localhost:3001` and add Prometheus as a data source.

## Troubleshooting

### Service won't start

```bash
# Check logs for errors
docker compose -f docker-compose.prod.yml logs <service-name>

# Rebuild a specific service
docker compose -f docker-compose.prod.yml build --no-cache <service-name>
docker compose -f docker-compose.prod.yml up -d <service-name>
```

### Database connection refused

```bash
# Verify database is running and healthy
docker compose -f docker-compose.prod.yml ps db

# Check database logs
docker compose -f docker-compose.prod.yml logs db

# Verify connection from API container
docker compose -f docker-compose.prod.yml exec api python -c "
import asyncio, asyncpg
asyncio.run(asyncpg.connect('postgresql://vaf:changeme@db:5432/vaf'))
print('Connection OK')
"
```

### Out of memory

If services are being killed (OOMKilled):

```bash
# Check which service was killed
docker compose -f docker-compose.prod.yml ps

# Increase memory limits in docker-compose.prod.yml
# Or free memory on the host
docker system prune -f
```

### Slow performance

```bash
# Check resource usage
docker stats

# Check PostgreSQL connections
docker compose -f docker-compose.prod.yml exec db \
  psql -U vaf -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis memory usage
docker compose -f docker-compose.prod.yml exec redis redis-cli info memory
```

### Resetting everything

```bash
# Stop all services and remove volumes (DATA LOSS!)
docker compose -f docker-compose.prod.yml down -v

# Remove all built images
docker compose -f docker-compose.prod.yml down --rmi all
```
