# deploy-prod

Prepare production deployment assets and a repeatable deployment pipeline.

## Arguments

$ARGUMENTS

Parse the following from the arguments:

- **platform**: deployment target (e.g., `aws`, `gcp`, `azure`, `docker-compose`, `railway`, `fly.io`, `vercel`)
- **region**: target region (e.g., `us-east-1`, `us-central1`)
- **runtime**: application runtime (e.g., `python3.11`, `node20`, `docker`)
- **database**: database system (e.g., `postgres`, `mongodb`, `sqlite`, `redis`)
- **secrets_source**: where secrets are managed (e.g., `env-file`, `aws-ssm`, `gcp-secrets`, `vault`, `doppler`)
- **zero_downtime**: whether zero-downtime deployment is required (`yes`/`no`)

---

## Process

### 1. Architecture Diagram
- Produce a deployment architecture diagram (Mermaid or ASCII) showing:
  - Compute resources (servers, containers, serverless functions)
  - Data stores (databases, caches, object storage)
  - Networking (load balancers, CDN, DNS)
  - External integrations (APIs, ML model endpoints)
  - Monitoring and logging infrastructure

### 2. Infrastructure / Platform Config
- Generate Infrastructure-as-Code or platform configuration:
  - **Docker**: `Dockerfile`, `docker-compose.prod.yml`
  - **AWS**: Terraform/CDK files or ECS task definitions
  - **GCP**: Cloud Run config or GKE manifests
  - **Fly.io/Railway**: `fly.toml` or `railway.json`
- Include environment-specific configs for staging vs production.

### 3. Build & Release Scripts
- Create build scripts that:
  - Install dependencies
  - Run linter and tests
  - Build production artifacts (compiled code, optimized images, bundled assets)
  - Tag the release with semantic versioning
- Output a single deployment command or script:
  ```bash
  ./scripts/deploy.sh --env production --region us-east-1
  ```

### 4. Rollout Strategy
- Define the deployment strategy:
  - **Rolling update**: gradual instance replacement
  - **Blue-green**: parallel environments with traffic switch
  - **Canary**: percentage-based traffic split
- Include rollback procedure:
  ```bash
  ./scripts/rollback.sh --to-version <previous-tag>
  ```

### 5. Observability
- Configure monitoring and alerting:
  - **Health checks**: endpoint paths and expected responses
  - **Logging**: structured logging format, log aggregation setup
  - **Metrics**: key metrics to track (latency, error rate, throughput, GPU utilization)
  - **Alerts**: conditions that trigger alerts (error rate > 5%, p99 > 2s)
- Recommend observability stack (e.g., Prometheus + Grafana, Datadog, CloudWatch).

### 6. Staging Deploy & Smoke Tests
- Deploy to staging environment first.
- Run automated smoke tests against staging:
  ```bash
  ./scripts/smoke-test.sh --env staging
  ```
- Verify core functionality before promoting to production.

---

## Output Requirements

- Infrastructure or workflow files in `infra/` or project root.
- `docs/deploy.md` with complete deployment documentation:
  - Prerequisites
  - Environment setup
  - Step-by-step deployment
  - Rollback procedure
  - Monitoring dashboard links
- A "how to deploy" command block:

```
## DEPLOYMENT COMMANDS

### First-time setup
<commands>

### Deploy to staging
<commands>

### Promote to production
<commands>

### Rollback
<commands>

### Health check
<commands>
```

- Fact Check List covering:
  - Region availability for chosen services
  - Pricing estimates for compute/storage
  - Rate limits on external APIs
  - SSL/TLS certificate requirements

---

## Example Invocation

```
/deploy-prod platform=docker-compose region=us-east-1 runtime=python3.11 database=postgres secrets_source=env-file zero_downtime=no
```
