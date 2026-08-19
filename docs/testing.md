# Testing Guide

## Overview

The VisionAudioForge test suite covers API contract validation, integration testing of vision/audio pipelines, authentication flows, model lifecycle, and search functionality.

## Directory Structure

```
backend/tests/
├── conftest.py                  # Shared fixtures (test_app, test_image, test_audio, auth_headers)
├── utils.py                     # Test utilities (image/audio generators, assertion helpers)
├── __init__.py
├── fixtures/
│   ├── sample_pipeline.json
│   ├── sample_experiment_config.json
│   └── sample_alert_rule.json
├── integration/
│   ├── test_vision_pipeline_e2e.py
│   ├── test_audio_pipeline_e2e.py
│   ├── test_model_lifecycle_e2e.py
│   ├── test_search_e2e.py
│   └── test_auth_flow_e2e.py
└── api/
    ├── test_all_endpoints_exist.py
    └── test_error_format.py
```

## Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# With coverage report
make test-coverage
```

Or directly with pytest:

```bash
cd backend
python -m pytest tests/ -v                          # all tests
python -m pytest tests/ -v -m unit                  # unit marker
python -m pytest tests/ -v -m integration           # integration marker
python -m pytest tests/ -v -k "test_auth"           # by name pattern
python -m pytest tests/ --cov=app --cov-report=html # HTML coverage report
```

## Test Markers

| Marker        | Description                           |
|---------------|---------------------------------------|
| `unit`        | Fast tests, no external dependencies  |
| `integration` | Requires app server or services       |
| `e2e`         | End-to-end full-stack tests           |
| `slow`        | Long-running tests                    |

## Test Utilities (`tests/utils.py`)

### Image Generators
- `create_test_image(width, height, color)` — solid-color RGB ndarray
- `create_test_image_with_shapes(width, height)` — image with rectangle and circle
- `image_to_png_bytes(image)` — encode ndarray to PNG bytes

### Audio Generators
- `create_test_audio(duration, sr, frequency)` — sine wave float32 ndarray
- `create_test_audio_with_noise(duration, sr, snr_db)` — sine + white noise
- `audio_to_wav_bytes(audio, sr)` — encode to WAV bytes

### Helpers
- `create_test_user_data()` — unique email/password/workspace_name dict
- `assert_response_shape(response, expected_keys)` — verify JSON keys
- `assert_paginated_response(response)` — verify pagination fields

## Fixtures (`conftest.py`)

| Fixture            | Description                                      |
|--------------------|--------------------------------------------------|
| `test_app`         | httpx AsyncClient bound to the FastAPI app        |
| `client`           | Alias for `test_app` (backward compat)            |
| `test_image`       | 100x100 gray PNG as bytes                         |
| `test_audio`       | 1s 440Hz sine WAV as bytes                        |
| `auth_headers`     | `{"Authorization": "Bearer <token>"}` dict        |
| `test_workspace_id`| UUID string for test workspace                    |

## CI/CD

GitHub Actions runs on every push and pull request (`.github/workflows/test.yml`). The workflow provisions PostgreSQL 16 and Redis 7 as service containers and runs the full test suite with coverage reporting.

## Coverage

Coverage is configured in `backend/pyproject.toml` with a minimum threshold of 50%. Source directory is `app/`, excluding tests and migrations.

```bash
make test-coverage   # generates HTML report in htmlcov/
```

## Environment Variables for Testing

| Variable         | Test Value                                             |
|------------------|--------------------------------------------------------|
| `POSTGRES_HOST`  | `localhost`                                            |
| `POSTGRES_PORT`  | `5432`                                                 |
| `POSTGRES_USER`  | `vaf`                                                  |
| `POSTGRES_DB`    | `vaf_test`                                             |
| `REDIS_HOST`     | `localhost`                                            |
| `JWT_SECRET_KEY` | `test-secret-key`                                      |
| `APP_ENV`        | `test`                                                 |

---

## Browser E2E (`frontend/e2e`)

Playwright drives a real browser against the full compose stack through nginx —
not a dev server, and not a mocked API. Bring the stack up first:

```bash
HTTP_PORT=8080 FRONTEND_PORT=3001 docker compose up -d
cd frontend && npx playwright test          # or: scripts/e2e.sh
```

Two rules this suite holds to:

- **No auth bypass.** `auth.setup.ts` registers a real user through the real
  form and banks the session. Nothing sets `AUTH_REQUIRED=false` and nothing
  stubs a token, so if registration breaks the whole suite fails — which is the
  point.
- **A broken feature is named, not accommodated.** When a journey cannot pass
  because the product is broken, it is marked `test.fixme` with the exact error
  and listed below. Weakening the assertion until it passes would convert a
  finding into a green tick.

### What each spec covers

| Spec | Covers |
| --- | --- |
| `console.spec.ts` | every dashboard page mounts without an error boundary |
| `auth-guard.anon.spec.ts` | anonymous callers are bounced from protected routes |
| `journeys.spec.ts` | vision analysis; pipeline template load/save/run |
| `work-journeys.spec.ts` | search, alerts, investigate, train, annotate, capture, audio, transform |
| `pipeline-templates.spec.ts` | every shipped template validates against the node registry |
| `providerless.spec.ts` | endpoints with no provider keep admitting it |

### Open defects these tests name

Each is `test.fixme` with the error in the spec. None is in this workstream's
files; all reproduce outside the browser.

| Area | Symptom | Cause |
| --- | --- | --- |
| Search | `POST /api/search/query` → 500 | `PermissionError: '/home/appuser'` — the image runs as non-root with no writable HOME, so huggingface_hub cannot cache CLIP weights |
| Audio analyse / transform / translate | 400 "cannot cache function `__o_fold`" | librosa's numba kernels use `cache=True`; site-packages is not writable by that user and `NUMBA_CACHE_DIR` is unset. Verified in-container that setting it to a writable path fixes all three |
| Pipeline save | `POST /api/pipeline/create` and `/save` → 500 | both pass `description=` to a `Pipeline` model that has no such column, so no pipeline can be persisted by any client |
| Pipeline templates in the console | save → 422 "missing required param 'image'" | `loadDefinitionToCanvas` drops `from_port`/`to_port` and `buildDefinition` re-emits every edge as `output`→`input`, ports these nodes do not have |
| Investigate | case creation → 401 | uses the bare `axios` module rather than the configured client, so no Authorization header; also posts straight to `:8000` past nginx and hardcodes a workspace id |
| Annotate | `GET /api/annotate/assets` → 500 | the query does not match the schema it runs against, so the studio shows "No assets loaded" for a dataset that has an image |

The first two share a root cause: caches that assume a writable home directory
in an image that does not give the runtime user one.

### Addressing elements

Prefer role and text. Two fields are addressed by placeholder because they have
no associated label — the search query box, and RuleBuilder's "Rule Name",
which renders as a bare `<label>` with no `htmlFor` next to an input with no
`id`. Both are worth fixing for screen readers. No `data-testid` was needed.
