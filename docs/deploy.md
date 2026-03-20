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
chmod +x scripts/deploy-prod.sh
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

### 3. Run Migrations

```bash
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

### 4. Verify Deployment

```bash
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/api/health
curl http://localhost:3000
```

## Environment Variables Reference

| Variable | Description | Default | Required |
|---|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://vaf:changeme@db:5432/vaf` | Yes |
| `POSTGRES_PASSWORD` | Database password | `changeme` | Yes |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` | Yes |
| `MINIO_ENDPOINT` | MinIO S3 endpoint | `minio:9000` | Yes |
| `MINIO_ROOT_USER` | MinIO admin username | `minioadmin` | Yes |
| `MINIO_ROOT_PASSWORD` | MinIO admin password | `minioadmin` | Yes |
| `MINIO_BUCKET` | Default S3 bucket | `vaf-assets` | Yes |
| `JWT_SECRET` | JWT signing secret | `change-me-in-production` | Yes |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | No |
| `JWT_EXPIRE_MINUTES` | Token expiry in minutes | `30` | No |
| `ANTHROPIC_API_KEY` | Anthropic API key | - | Yes |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://redis:6379/1` | Yes |
| `LOG_LEVEL` | Application log level | `INFO` | No |

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
