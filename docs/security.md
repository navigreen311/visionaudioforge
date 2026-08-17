# Security Documentation

## Authentication Overview

VisionAudioForge uses a dual authentication scheme:

### JWT (JSON Web Tokens)
- **Access tokens** expire after **30 minutes** and are used for all authenticated API requests.
- **Refresh tokens** expire after **7 days** and can be exchanged for new access tokens via `POST /api/auth/refresh`.
- Tokens are signed with HS256 using a secret loaded from the `JWT_SECRET_KEY` environment variable.
- The backend will emit a warning at startup if the secret is set to the insecure default.

### API Keys
- Service-to-service communication uses API keys managed through the developer portal.
- API keys are hashed with **SHA-256** before storage; the raw key is shown only once at creation time. A fast hash is the right choice here — unlike a password, an API key is a high-entropy value this system generated, so there is no low-entropy guess space for an attacker to grind through and nothing for a slow KDF to buy.
- **Passwords** are a different matter and use **bcrypt at cost factor 12** (`app/core/security.py`). Inputs are truncated to bcrypt's 72-byte limit, which the algorithm ignores past regardless.

## RBAC Roles and Permissions

| Role        | Description                              | Key Permissions                         |
|-------------|------------------------------------------|-----------------------------------------|
| `admin`     | Full platform access                     | User management, system configuration   |
| `manager`   | Workspace-level management               | Invite users, manage datasets, pipelines|
| `analyst`   | Standard operational access              | Run experiments, view results, annotate  |
| `viewer`    | Read-only access                         | View dashboards, reports, annotations   |
| `service`   | Machine-to-machine (API key auth only)   | Scoped per-key to specific endpoints    |

Permissions are enforced at the route level via FastAPI dependencies (`get_current_user`, role checks).

## Data Encryption

### At Rest
- PostgreSQL uses transparent data encryption (TDE) when deployed on managed cloud providers (e.g., AWS RDS, Azure Database).
- MinIO object storage supports server-side encryption (SSE-S3 / SSE-KMS).
- Sensitive configuration values are stored as environment variables, never in source code.

### In Transit
- All external traffic is served over HTTPS via the nginx reverse proxy.
- Internal service-to-service traffic runs over Docker's internal network; TLS can be enabled for zero-trust deployments.

## Secret Management Best Practices

1. **Never hardcode secrets** in source code. Use environment variables or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault).
2. **Rotate secrets regularly** — especially `JWT_SECRET_KEY`, database passwords, and API keys.
3. **Use `.env` files only in development** and ensure `.env` is listed in `.gitignore`.
4. **Audit secret access** using the platform's audit logging middleware.
5. **Minimum privilege** — each service should only have access to the secrets it needs.

### Required Environment Variables

| Variable            | Purpose                        | Default (dev only)         |
|---------------------|--------------------------------|----------------------------|
| `JWT_SECRET_KEY`    | Signs JWT tokens               | `change-me-jwt-secret`     |
| `POSTGRES_PASSWORD` | Database authentication        | `change-me-db-password`    |
| `REDIS_PASSWORD`    | Redis authentication           | `change-me-redis-password` |
| `MINIO_ACCESS_KEY`  | Object storage access          | `minioaccess`              |
| `MINIO_SECRET_KEY`  | Object storage secret          | `miniosecret`              |
| `CORS_ORIGINS`      | Comma-separated allowed origins| `http://localhost:3000`    |

## Security Headers Configuration

The nginx reverse proxy adds the following headers to all responses:

| Header                        | Value                                 | Purpose                              |
|-------------------------------|---------------------------------------|--------------------------------------|
| `X-Content-Type-Options`      | `nosniff`                             | Prevent MIME-type sniffing           |
| `X-Frame-Options`             | `DENY`                                | Prevent clickjacking                 |
| `X-XSS-Protection`            | `1; mode=block`                       | Legacy XSS filter                    |
| `Strict-Transport-Security`   | `max-age=31536000; includeSubDomains` | Force HTTPS for 1 year               |
| `Content-Security-Policy`     | `default-src 'self'`                  | Restrict resource loading to origin  |
| `Referrer-Policy`             | `strict-origin-when-cross-origin`     | Control referrer information leakage |

## Rate Limiting Configuration

Auth endpoints (`/api/auth/*`) are protected by an in-memory sliding-window rate limiter:

- **Limit**: 100 requests per minute per IP address
- **Scope**: All routes under the `/api/auth` prefix (register, login, refresh, logout)
- **Response**: HTTP 429 (Too Many Requests) when the limit is exceeded
- **IP detection**: Uses `X-Forwarded-For` header (behind nginx proxy) or direct client IP

For production deployments with multiple backend instances, replace the in-memory limiter with a Redis-backed implementation to share state across processes.

## Reporting Vulnerabilities

If you discover a security vulnerability in VisionAudioForge:

1. **Do not** open a public GitHub issue.
2. Email **security@visionaudioforge.dev** with:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Your suggested fix (if any)
3. You will receive an acknowledgment within **48 hours**.
4. We follow coordinated disclosure: fixes are developed privately, and credit is given in the release notes after the patch is deployed.
