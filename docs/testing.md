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
