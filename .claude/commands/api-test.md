# api-test

Generate API contract + integration tests from OpenAPI/GraphQL specs or live endpoints.

## Arguments

$ARGUMENTS

Parse the following from the arguments:

- **spec_path_or_url**: path to OpenAPI/GraphQL spec file, or a live base URL to probe
- **auth_mode**: authentication method: `none`, `api-key`, `bearer`, `oauth2`, `basic`
- **env**: target environment: `local`, `staging`, `production`
- **test_style**: test framework/style: `pytest`, `jest`, `httpx`, `requests`, `supertest`
- **load_smoke**: (optional) whether to include basic load/smoke tests: `yes`/`no` (default: `no`)

---

## Process

### 1. Parse Spec or Discover Endpoints
- If `spec_path_or_url` is a file (`.json`, `.yaml`, `.graphql`):
  - Parse the spec and extract all endpoints, methods, parameters, request/response schemas.
- If `spec_path_or_url` is a URL:
  - Check for `/openapi.json`, `/docs`, `/swagger.json`, `/graphql` introspection.
  - If no spec found, probe common endpoint patterns and document discovered routes.
- Output an endpoint inventory:

```
## Discovered Endpoints
| Method | Path | Auth | Request Body | Response |
|--------|------|------|-------------|----------|
| POST | /api/preprocess | api-key | ImageInput | ProcessedImage |
| GET | /api/health | none | — | HealthStatus |
```

### 2. Generate Success Tests
For each endpoint, create tests covering:
- **Happy path**: valid request → expected response status and shape.
- **Response schema validation**: verify response matches spec types and required fields.
- **Content-type verification**: correct `Content-Type` headers.
- **Pagination** (if applicable): verify pagination params work correctly.

### 3. Generate Error Tests
For each endpoint, create tests covering:
- **400 Bad Request**: malformed body, missing required fields, invalid types.
- **401 Unauthorized**: missing or invalid auth credentials.
- **403 Forbidden**: valid auth but insufficient permissions (if applicable).
- **404 Not Found**: non-existent resource IDs.
- **422 Unprocessable Entity**: valid structure but semantically invalid data.
- **429 Rate Limited**: if rate limiting is documented (optional).
- **500 handling**: verify error responses have consistent error format.

### 4. Create Reusable Client & Helpers
- Build a test client/helper module:
  ```
  tests/api/
  ├── conftest.py          # fixtures, auth setup, base URL config
  ├── client.py            # reusable API client wrapper
  ├── helpers.py           # response validators, data generators
  ├── test_health.py       # health check tests
  ├── test_<resource>.py   # per-resource test files
  └── data/
      └── fixtures.json    # sample request/response data
  ```
- Include auth setup that reads credentials from environment variables.
- Create response validator helpers that check status, schema, and headers.

### 5. CLI for Multiple Environments
- Create a test runner that accepts environment as a parameter:
  ```bash
  # Run against local
  API_BASE_URL=http://localhost:8000 pytest tests/api/ -v

  # Run against staging
  API_BASE_URL=https://staging.example.com API_KEY=$STAGING_KEY pytest tests/api/ -v
  ```
- Document environment variables needed per env.

### 6. Load Smoke Tests (if requested)
- If `load_smoke=yes`, generate basic load tests:
  - Hit key endpoints with 10-50 concurrent requests.
  - Measure response times (p50, p95, p99).
  - Verify no errors under moderate load.
  - Use `locust`, `k6`, or simple async scripts depending on stack.

### 7. Run & Summarize

```
## API TEST RESULTS

### Endpoint Coverage
| Endpoint | Success Tests | Error Tests | Status |
|----------|--------------|-------------|--------|
| POST /api/preprocess | 3 | 4 | PASS |
| GET /api/health | 1 | 0 | PASS |

### Summary
- Total tests: X
- Passed: Y
- Failed: Z
- Skipped: W

### Commands
- Run all: `pytest tests/api/ -v`
- Run single endpoint: `pytest tests/api/test_preprocess.py -v`
- Run with auth: `API_KEY=xxx pytest tests/api/ -v`

### Report
- Console output: above
- HTML report: `reports/api-test-report.html` (if configured)
```

---

## Output Requirements

- Test files in `tests/api/` with runnable suites.
- Reusable client/helper modules.
- Example commands for each environment.
- Test result summary with pass/fail counts.
- Report paths documented.

---

## Example Invocation

```
/api-test spec_path_or_url=openapi.yaml auth_mode=api-key env=local test_style=pytest load_smoke=yes
```
