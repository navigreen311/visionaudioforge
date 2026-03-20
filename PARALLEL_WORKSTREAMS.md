# VisionAudioForge — 20 Parallel Workstreams

## How to Run

Open 20 terminal windows. In each one:

```bash
cd C:\Users\Shadow\projects\vision-audio-ai
git worktree add ../vaf-ws<NN>-<name> ai-feature/ws<NN>-<name>
cd ../vaf-ws<NN>-<name>
claude
```

Then paste the corresponding prompt below into each Claude Code instance.

### After all 20 complete — Merge Sequence:

```bash
cd C:\Users\Shadow\projects\vision-audio-ai

# Merge in dependency order (infra first, features next, testing last)
git merge ai-feature/ws01-docker-infra --no-ff -m "merge: ws01 docker infrastructure"
git merge ai-feature/ws02-database-migrations --no-ff -m "merge: ws02 database migrations"
git merge ai-feature/ws03-auth-system --no-ff -m "merge: ws03 auth system"
git merge ai-feature/ws04-health-observability --no-ff -m "merge: ws04 health & observability"
git merge ai-feature/ws05-vision-preprocessing --no-ff -m "merge: ws05 vision preprocessing"
git merge ai-feature/ws06-vision-optical-flow --no-ff -m "merge: ws06 vision optical flow"
git merge ai-feature/ws07-vision-detection --no-ff -m "merge: ws07 vision detection"
git merge ai-feature/ws08-audio-spectral --no-ff -m "merge: ws08 audio spectral analysis"
git merge ai-feature/ws09-audio-augmentation --no-ff -m "merge: ws09 audio augmentation"
git merge ai-feature/ws10-capture-engine --no-ff -m "merge: ws10 capture engine"
git merge ai-feature/ws11-model-registry --no-ff -m "merge: ws11 model registry"
git merge ai-feature/ws12-experiment-tracker --no-ff -m "merge: ws12 experiment tracker"
git merge ai-feature/ws13-dataset-manager --no-ff -m "merge: ws13 dataset manager"
git merge ai-feature/ws14-faiss-search --no-ff -m "merge: ws14 FAISS search"
git merge ai-feature/ws15-pipeline-builder --no-ff -m "merge: ws15 pipeline builder"
git merge ai-feature/ws16-copilot-agent --no-ff -m "merge: ws16 copilot agent"
git merge ai-feature/ws17-transform-audio --no-ff -m "merge: ws17 audio transform"
git merge ai-feature/ws18-transform-video --no-ff -m "merge: ws18 video transform"
git merge ai-feature/ws19-frontend-dashboard --no-ff -m "merge: ws19 frontend dashboard"
git merge ai-feature/ws20-testing-e2e --no-ff -m "merge: ws20 e2e testing"

# Cleanup worktrees
for i in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20; do
  git worktree remove ../vaf-ws${i}-* --force 2>/dev/null
done
```

---

## WORKSTREAM 01 — Docker Infrastructure & DevOps
**Branch:** `ai-feature/ws01-docker-infra`
**Scope:** infra

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws01-docker-infra.

YOUR TASK: Build production-ready Docker infrastructure.

Read CLAUDE.md for project context and conventions. Then implement:

1. DOCKER COMPOSE (docker-compose.yml) — make it fully functional:
   - api: FastAPI on 8000, Dockerfile builds from backend/, hot-reload via volume mount, depends_on db/redis
   - frontend: Next.js on 3000, Dockerfile builds from frontend/, hot-reload
   - db: PostgreSQL 16, persistent volume, health check (pg_isready), init script creates DB + enables pgvector
   - redis: Redis 7 with AOF persistence, health check
   - minio: MinIO on 9000/9001, default bucket creation via entrypoint
   - nginx: reverse proxy on 80, config from nginx/nginx.conf
   - celery_worker: same image as api, runs celery worker command

2. DOCKERFILES:
   - backend/Dockerfile: multi-stage (builder + runtime), Python 3.11-slim, install system deps (libgl1, libglib2.0, ffmpeg), pip install requirements.txt, non-root user
   - frontend/Dockerfile: multi-stage, node:20-alpine, npm ci, next build, standalone output

3. NGINX CONFIG (nginx/nginx.conf):
   - / → frontend:3000
   - /api → api:8000 (strip /api prefix? No, keep it)
   - /ws → api:8000 with WebSocket upgrade headers
   - Gzip compression, proper MIME types, security headers

4. ENVIRONMENT:
   - .env.example with ALL variables (DATABASE_URL, REDIS_URL, MINIO_*, JWT_SECRET, ANTHROPIC_API_KEY, etc.)
   - scripts/setup.sh: copy .env.example → .env if missing, docker compose build

5. MAKEFILE TARGETS: dev, build, stop, clean, logs, db-shell, redis-shell

6. INIT SCRIPTS:
   - scripts/init-db.sql: CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm;
   - scripts/init-minio.sh: create default bucket via mc client

TEST: Run `docker compose config` to validate. All services must parse correctly.
COMMIT with conventional commits. Update CHANGELOG.md.
```

---

## WORKSTREAM 02 — Database Migrations & Models
**Branch:** `ai-feature/ws02-database-migrations`
**Scope:** api

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws02-database-migrations.

YOUR TASK: Complete all SQLAlchemy models and create Alembic migrations.

Read CLAUDE.md for context. Read backend/app/models/ to see existing stubs. Then implement:

1. COMPLETE ALL MODELS in backend/app/models/:
   - workspace.py: Workspace(id UUID, name, slug unique, owner_id FK→users, plan enum[free/pro/enterprise], settings JSONB, created_at, updated_at)
   - user.py: User(id UUID, email unique, hashed_password, role enum[admin/operator/analyst/viewer], workspace_id FK→workspaces, last_login, created_at)
   - model_registry.py: ModelRecord(id UUID, name, version str, status enum[registered/staging/production/shadow/archived], backbone, metrics JSONB, workspace_id FK, registered_at, updated_at)
   - experiment.py: Experiment(id UUID, name, config JSONB, status enum[created/running/completed/failed], best_epoch JSONB, model_id FK, workspace_id FK, created_at) + ExperimentEpoch(id, experiment_id FK, epoch int, metrics JSONB, timestamp)
   - dataset.py: Dataset(id UUID, name, modality enum[image/video/audio/multimodal], version, stats JSONB, workspace_id FK, created_at)
   - asset.py: Asset(id UUID, type enum[image/video/audio], path, filename, size_bytes, metadata JSONB, tags ARRAY[str], workspace_id FK, created_at)
   - pipeline.py: Pipeline(id UUID, name, version, definition JSONB, status, workspace_id FK) + PipelineRun(id, pipeline_id FK, status enum[pending/running/completed/failed], started_at, finished_at, results JSONB)
   - alert.py: Alert(id UUID, rule_id FK, severity enum[critical/high/medium/low], payload JSONB, status enum[new/acknowledged/resolved/dismissed], acknowledged_by FK→users, workspace_id FK) + AlertRule(id UUID, name, conditions JSONB, actions JSONB, enabled bool, workspace_id FK)
   - embedding.py: Embedding(id UUID, asset_id FK, modality, vector Column(Vector(512)) for pgvector, model_name, created_at)
   - event.py: Event(id UUID, type, payload JSONB, timestamp, source, workspace_id FK, linked_asset_ids ARRAY[UUID])
   - audit_log.py: AuditLog(id UUID, user_id FK, action, resource, payload JSONB, timestamp, workspace_id FK)
   - agent.py: Agent(id UUID, name, agent_type, config JSONB, status, workspace_id FK) + AgentMemory(id UUID, agent_id FK, content text, importance_score float, freshness_score float, created_at, expires_at)

2. Add proper relationships (back_populates), indexes on workspace_id and created_at, and __tablename__.

3. Create ALEMBIC MIGRATION:
   - Configure alembic/env.py to use async engine and import all models
   - Generate initial migration: all 15+ tables
   - Migration file should be clean and reviewable

4. Add PYDANTIC SCHEMAS in backend/app/schemas/:
   - One schema file per model: create, read, update variants
   - common.py: PaginatedResponse[T], ErrorResponse, SuccessResponse

5. TESTS:
   - backend/tests/test_models.py: verify all models can be instantiated
   - backend/tests/test_schemas.py: verify schema validation

COMMIT with conventional commits. Update CHANGELOG.md.
```

---

## WORKSTREAM 03 — Auth System
**Branch:** `ai-feature/ws03-auth-system`
**Scope:** api

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws03-auth-system.

YOUR TASK: Implement complete JWT authentication and RBAC.

Read CLAUDE.md for context. Then implement:

1. SECURITY CORE (backend/app/core/security.py):
   - Password hashing with bcrypt (passlib)
   - JWT token creation (access + refresh tokens) using python-jose
   - Token verification and decoding
   - Role-based access control decorator/dependency

2. AUTH ROUTES (backend/app/api/routes/auth.py):
   - POST /api/auth/register — create user + workspace, return tokens
   - POST /api/auth/login — verify credentials, return access + refresh tokens
   - POST /api/auth/refresh — refresh token rotation
   - GET /api/auth/me — get current user profile
   - PUT /api/auth/me — update profile
   - POST /api/auth/logout — blacklist token (Redis-based)

3. DEPENDENCIES (backend/app/core/deps.py):
   - get_db: async session dependency
   - get_current_user: extract user from JWT, verify in DB
   - require_role(roles): dependency that checks user role
   - get_workspace: extract workspace from current user

4. MIDDLEWARE:
   - backend/app/middleware/audit.py: log all API calls to audit_logs table (user, action, resource, timestamp)

5. SCHEMAS (backend/app/schemas/auth.py):
   - LoginRequest, RegisterRequest, TokenResponse, UserResponse, UserUpdate

6. TESTS (backend/tests/test_auth.py):
   - test_register_creates_user_and_workspace
   - test_login_returns_tokens
   - test_invalid_login_returns_401
   - test_protected_route_requires_token
   - test_role_based_access
   - test_refresh_token_rotation

COMMIT with conventional commits. Update CHANGELOG.md.
```

---

## WORKSTREAM 04 — Health & Observability
**Branch:** `ai-feature/ws04-health-observability`
**Scope:** api

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws04-health-observability.

YOUR TASK: Implement health checks, structured logging, and observability.

Read CLAUDE.md for context. Then implement:

1. HEALTH ENDPOINT (backend/app/api/routes/health.py):
   - GET /api/health — check DB connection, Redis ping, MinIO connectivity
   - Return: {"status": "healthy/degraded/unhealthy", "services": {"db": "up", "redis": "up", "minio": "up"}, "version": "1.0.0", "uptime": "..."}

2. STRUCTURED LOGGING (backend/app/core/logging.py):
   - JSON-formatted structured logging
   - Request ID middleware (generate UUID per request, attach to all logs)
   - Log: method, path, status_code, duration_ms, user_id, workspace_id
   - Configure log levels from env var

3. METRICS (backend/app/core/metrics.py):
   - Request count by endpoint
   - Request duration histogram
   - Active WebSocket connections gauge
   - Inference job queue depth
   - Use prometheus_client library

4. OPENTELEMETRY (backend/app/core/telemetry.py):
   - Basic OpenTelemetry setup for distributed tracing
   - Trace incoming requests
   - Span for database queries and external API calls

5. MIDDLEWARE:
   - backend/app/middleware/timing.py: add X-Process-Time header to all responses
   - backend/app/middleware/request_id.py: add X-Request-ID header

6. METRICS ENDPOINT:
   - GET /api/metrics — Prometheus-compatible metrics endpoint

7. TESTS:
   - test_health_endpoint_returns_status
   - test_request_id_header_added
   - test_timing_header_added

COMMIT with conventional commits. Update CHANGELOG.md.
```

---

## WORKSTREAM 05 — Vision Preprocessing Service
**Branch:** `ai-feature/ws05-vision-preprocessing`
**Scope:** api

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws05-vision-preprocessing.

YOUR TASK: Implement the complete vision preprocessing service (M2 partial).

Read CLAUDE.md for domain context on image preprocessing. Then implement:

1. SERVICE (backend/app/services/vision/preprocessing.py):
   - ImagePreprocessor class with:
     - min_max_normalize(image, target_range=(0,1)) → normalized image
     - z_score_normalize(image, global_stats=None) → standardized image
     - per_channel_normalize(image) → per-channel standardized
     - convert_color_space(image, from_space, to_space) — support RGB, BGR, HSV, LAB, Grayscale
     - histogram_equalization(image)
     - edge_detection(image, method='canny', params={})
     - resize(image, width, height, maintain_aspect=True)
     - preprocess_pipeline(image, steps=[]) — chain multiple operations

2. API ROUTE (backend/app/api/routes/vision.py):
   - POST /api/vision/analyze — accept image upload (multipart), operations list in body
     - Parse operations: ["normalize:min_max", "color:hsv", "edge:canny"]
     - Apply operations sequentially
     - Return: processed image (base64), metadata (shape, dtype, stats), processing_time_ms
   - POST /api/vision/screen-analyze — accept screenshot, run OCR + brightness + edge density
     - Return: {"text": "...", "brightness": 0.7, "edge_density": 0.3, "colors": {...}}

3. SCHEMAS (backend/app/schemas/vision.py):
   - VisionAnalyzeRequest, VisionAnalyzeResponse, ScreenAnalyzeResponse
   - Include operation definitions as enums

4. UTILITIES (backend/app/services/vision/utils.py):
   - image_to_base64, base64_to_image
   - calculate_image_stats (mean, std, min, max per channel)
   - validate_image (check format, size limits)

5. TESTS (backend/tests/test_vision_preprocessing.py):
   - test_min_max_normalizes_to_0_1
   - test_z_score_has_zero_mean
   - test_color_space_rgb_to_hsv
   - test_color_space_rgb_to_grayscale
   - test_edge_detection_canny
   - test_preprocessing_pipeline_chains
   - test_api_analyze_endpoint
   - test_screen_analyze_returns_ocr

COMMIT with conventional commits. Update CHANGELOG.md. Add docs/vision-preprocessing.md.
```

---

## WORKSTREAM 06 — Vision Optical Flow & Motion
**Branch:** `ai-feature/ws06-vision-optical-flow`
**Scope:** api

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws06-vision-optical-flow.

YOUR TASK: Implement optical flow and frame differencing services (M2 partial).

Read CLAUDE.md for domain context on optical flow. Then implement:

1. SERVICE (backend/app/services/vision/motion.py):
   - MotionAnalyzer class with:
     - lucas_kanade(prev_frame, curr_frame, params=None) → tracked points, motion vectors, magnitudes
     - farneback_dense(prev_frame, curr_frame, params=None) → flow field, magnitude, angle
     - frame_diff_consecutive(prev_frame, curr_frame, threshold=25) → motion_mask, motion_percentage
     - frame_diff_background(frames, method='MOG2') → foreground masks
     - frame_diff_three_frame(f1, f2, f3, threshold=25) → refined motion mask
     - motion_heatmap(flow) → HSV-colored motion visualization
     - compute_motion_stats(motion_data) → {"mean_magnitude", "max_magnitude", "motion_area_pct", "dominant_direction"}

2. API ROUTES (backend/app/api/routes/vision.py — extend):
   - POST /api/vision/optical-flow — accept 2 frames (multipart), method param (lucas-kanade/farneback)
     - Return: motion vectors (JSON), visualization (base64), stats
   - POST /api/vision/frame-diff — accept 2+ frames, method (consecutive/background/three-frame)
     - Return: motion mask (base64), motion_percentage, motion_stats

3. VISUALIZATION (backend/app/services/vision/visualization.py):
   - draw_optical_flow_arrows(image, flow, step=16, scale=3)
   - create_motion_heatmap(flow) → HSV colored image
   - draw_tracked_points(image, old_pts, new_pts, colors)
   - side_by_side_comparison(img1, img2, title1, title2)

4. TESTS (backend/tests/test_vision_motion.py):
   - test_lucas_kanade_detects_motion
   - test_farneback_returns_dense_flow
   - test_frame_diff_detects_changes
   - test_three_frame_reduces_noise
   - test_motion_heatmap_valid_hsv
   - test_api_optical_flow_endpoint
   - test_api_frame_diff_endpoint

COMMIT with conventional commits. Add docs/vision-motion.md.
```

---

## WORKSTREAM 07 — Vision Detection & Specialized
**Branch:** `ai-feature/ws07-vision-detection`
**Scope:** api

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws07-vision-detection.

YOUR TASK: Implement object detection, OCR, and specialized vision features (M2 partial).

Read CLAUDE.md for context. Then implement:

1. SERVICE (backend/app/services/vision/detection.py):
   - ObjectDetector class:
     - detect(image, model='yolov8n', confidence=0.5, classes=None) → list of Detection(bbox, class, confidence, label)
     - detect_batch(images, ...) → list of detection results
   - Load YOLOv8 model (ultralytics library) — use nano model for V1

2. SERVICE (backend/app/services/vision/ocr.py):
   - OCREngine class:
     - extract_text(image) → {"text": str, "blocks": [{"text", "bbox", "confidence"}]}
     - Use pytesseract or easyocr

3. SERVICE (backend/app/services/vision/specialized.py):
   - face_detect(image) → list of face bounding boxes
   - pose_estimate(image) → keypoints (use mediapipe or basic OpenCV)
   - anomaly_score(image, reference_images) → float anomaly score

4. ERROR ANALYSIS (backend/app/services/vision/error_analysis.py):
   - compute_confusion_matrix(predictions, ground_truth, classes)
   - class_level_metrics(cm) → per-class precision, recall, F1
   - error_clustering(errors, features) → grouped error patterns
   - generate_quality_report(metrics) → structured report dict

5. API ROUTES — extend backend/app/api/routes/vision.py:
   - POST /api/vision/detect — image + params → detections
   - POST /api/vision/ocr — image → extracted text
   - POST /api/vision/error-analysis — predictions + ground_truth → report

6. TESTS:
   - test_yolo_detection_returns_boxes (use synthetic image)
   - test_ocr_extracts_text
   - test_confusion_matrix_computation
   - test_api_detect_endpoint

COMMIT with conventional commits. Add docs/vision-detection.md.
```

---

## WORKSTREAM 08 — Audio Spectral Analysis
**Branch:** `ai-feature/ws08-audio-spectral`
**Scope:** api

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws08-audio-spectral.

YOUR TASK: Implement complete audio spectral analysis service (M3 partial).

Read CLAUDE.md for domain context on STFT, MEL, MFCC. Then implement:

1. SERVICE (backend/app/services/audio/spectral.py):
   - SpectralAnalyzer class:
     - compute_stft(audio, sr, n_fft=2048, hop_length=512, window='hann') → spectrogram (complex), magnitude, phase
     - compute_mel_spectrogram(audio, sr, n_mels=128, n_fft=2048, hop_length=512) → mel spectrogram
     - compute_mfcc(audio, sr, n_mfcc=13, n_fft=2048, hop_length=512) → MFCCs + delta + delta-delta
     - compute_power_spectrogram(audio, sr) → power spectrogram
     - compute_waveform_stats(audio, sr) → {"duration", "sample_rate", "rms", "peak", "zero_crossing_rate"}
     - extract_all_features(audio, sr) → combined feature dict

2. SERVICE (backend/app/services/audio/io.py):
   - load_audio(file_path_or_bytes, sr=None) → (audio_array, sample_rate)
   - save_audio(audio, sr, path, format='wav')
   - audio_to_base64(audio, sr, format='wav') → base64 string
   - validate_audio(file) → check format, duration limits, sample rate

3. API ROUTE (backend/app/api/routes/audio.py):
   - POST /api/audio/analyze — accept audio upload + operations list
     - Operations: ["stft", "mel", "mfcc", "waveform", "all"]
     - Return: requested features as JSON arrays + visualization images (base64 spectrograms)

4. VISUALIZATION (backend/app/services/audio/visualization.py):
   - plot_spectrogram(spec, sr, hop_length, title) → base64 PNG
   - plot_mel_spectrogram(mel_spec, sr, hop_length) → base64 PNG
   - plot_mfcc(mfcc, sr, hop_length) → base64 PNG
   - plot_waveform(audio, sr) → base64 PNG

5. TESTS (backend/tests/test_audio_spectral.py):
   - test_stft_shape_correct
   - test_mel_spectrogram_shape
   - test_mfcc_13_coefficients
   - test_delta_mfcc_computed
   - test_waveform_stats_valid
   - test_api_audio_analyze_stft
   - test_api_audio_analyze_mfcc

COMMIT with conventional commits. Add docs/audio-spectral.md.
```

---

## WORKSTREAM 09 — Audio Augmentation Pipeline
**Branch:** `ai-feature/ws09-audio-augmentation`
**Scope:** api

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws09-audio-augmentation.

YOUR TASK: Implement the complete audio augmentation pipeline (M3 partial).

Read CLAUDE.md for domain context on audio augmentation. Then implement:

1. SERVICE (backend/app/services/audio/augmentation.py):
   - AudioAugmenter class with configurable pipeline:
     - add_noise(audio, sr, noise_type='white', snr_db=20) — white, pink, environmental
     - time_stretch(audio, sr, rate=1.0) — 0.5x to 2.0x
     - pitch_shift(audio, sr, n_steps=0) — semitone-precise, ±12
     - time_shift(audio, sr, shift_ms=0) — positive/negative shift
     - frequency_mask(spec, num_masks=1, mask_width=10) — SpecAugment
     - time_mask(spec, num_masks=1, mask_width=10) — SpecAugment
     - apply_pipeline(audio, sr, config) — chain augmentations with probabilities
     - augment_batch(audio_files, config, num_versions=3) — generate N augmented versions per file

2. PIPELINE CONFIG SCHEMA:
   - AugmentationConfig: list of (augmentation_type, probability, params) tuples
   - Predefined presets: "speech_robust", "music_robust", "environmental", "light", "heavy"

3. API ROUTE — extend backend/app/api/routes/audio.py:
   - POST /api/audio/augment — accept audio + augmentation config JSON
     - Return: augmented audio (base64), applied_augmentations list, comparison visualization

4. TESTS (backend/tests/test_audio_augmentation.py):
   - test_add_white_noise_changes_audio
   - test_time_stretch_changes_duration
   - test_pitch_shift_preserves_duration
   - test_frequency_mask_zeros_bands
   - test_pipeline_applies_multiple
   - test_preset_configs_valid
   - test_api_augment_endpoint

COMMIT with conventional commits. Add docs/audio-augmentation.md.
```

---

## WORKSTREAM 10 — Live Capture Engine
**Branch:** `ai-feature/ws10-capture-engine`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws10-capture-engine.

YOUR TASK: Implement the live capture engine (M1) — WebRTC camera, screen, microphone.

Read CLAUDE.md for context. Then implement:

1. BACKEND WebSocket (backend/app/ws/capture.py):
   - WebSocket endpoint: ws://api/live/stream
   - Accept video frames (base64), run lightweight analysis, return results
   - Handle connection lifecycle: connect, receive frames, send analysis, disconnect
   - Support multiple concurrent streams per workspace

2. BACKEND SERVICE (backend/app/services/capture/manager.py):
   - CaptureSessionManager:
     - create_session(workspace_id, source_type, config) → session_id
     - process_frame(session_id, frame_data) → analysis results
     - end_session(session_id)
     - list_active_sessions(workspace_id) → active stream list

3. FRONTEND — Capture Page (frontend/src/app/(dashboard)/capture/page.tsx):
   - Camera capture: navigator.mediaDevices.getUserMedia video stream
   - Screen capture: navigator.mediaDevices.getDisplayMedia
   - Microphone: getUserMedia audio with real-time level meter
   - Multi-source switcher: toggle between camera/screen/multi-cam view
   - Stream frames to WebSocket at configurable FPS (default 5 for analysis)
   - Display AI HUD overlay (detection boxes, labels from WebSocket responses)

4. FRONTEND COMPONENTS:
   - frontend/src/components/capture/LiveFeedPanel.tsx — video element + canvas overlay + controls
   - frontend/src/components/capture/AudioMeter.tsx — real-time audio level visualization
   - frontend/src/components/capture/SourceSwitcher.tsx — camera/screen/mic selector
   - frontend/src/components/capture/CaptureControls.tsx — start/stop/record/snapshot buttons

5. TESTS:
   - Backend: test WebSocket connection lifecycle, test frame processing
   - Frontend: component renders without errors (basic smoke tests)

COMMIT with conventional commits. Add docs/capture-engine.md.
```

---

## WORKSTREAM 11 — Model Registry
**Branch:** `ai-feature/ws11-model-registry`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws11-model-registry.

YOUR TASK: Implement the Model Registry service (M6 partial).

Read CLAUDE.md for context. Then implement:

1. SERVICE (backend/app/services/models/registry.py):
   - ModelRegistryService:
     - register_model(name, version, backbone, metadata, workspace_id) → ModelRecord
     - get_model(model_id) → ModelRecord with metrics
     - list_models(workspace_id, status=None) → paginated list
     - update_status(model_id, new_status) — lifecycle: registered→staging→production→archived
     - compare_models(model_id_a, model_id_b) → side-by-side metrics comparison
     - rollback(model_id, to_version) → restore previous version to production
     - delete_model(model_id) — soft delete (archive)

2. API ROUTES (backend/app/api/routes/registry.py):
   - POST /api/registry/register — register new model
   - GET /api/registry/models — list models (filterable by status, backbone)
   - GET /api/registry/models/{id} — get single model
   - PUT /api/registry/models/{id}/status — promote/demote
   - POST /api/registry/compare — compare two models
   - POST /api/registry/models/{id}/rollback — rollback to version

3. FRONTEND (frontend/src/app/(dashboard)/train/page.tsx):
   - Model list table: name, version, status badge, backbone, metrics, actions
   - Model detail view: metrics charts, version history, promote/demote buttons
   - Compare modal: side-by-side metrics table
   - Register new model form

4. TESTS:
   - test_register_model, test_list_models_filtered, test_promote_model
   - test_compare_models, test_rollback, test_api_endpoints

COMMIT with conventional commits. Add docs/model-registry.md.
```

---

## WORKSTREAM 12 — Experiment Tracker
**Branch:** `ai-feature/ws12-experiment-tracker`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws12-experiment-tracker.

YOUR TASK: Implement the Experiment Tracker (M6 partial).

Read CLAUDE.md for context. Then implement:

1. SERVICE (backend/app/services/models/experiments.py):
   - ExperimentService:
     - create_experiment(name, config, model_id, workspace_id) → Experiment
     - log_epoch(experiment_id, epoch, metrics) → ExperimentEpoch
     - get_experiment(experiment_id) → Experiment with all epochs
     - list_experiments(workspace_id, model_id=None) → paginated list
     - get_best_checkpoint(experiment_id, metric='val_loss', mode='min') → epoch data
     - compare_experiments(exp_ids) → comparative metrics

2. TRAINING SERVICE (backend/app/services/models/training.py):
   - TransferLearningService:
     - start_finetune(config: FinetuneConfig) → job_id (runs via Celery)
     - FinetuneConfig: backbone, dataset_id, epochs, lr, batch_size, freeze_layers, gradient_clip
     - Implement actual ResNet/CLIP fine-tuning with PyTorch
     - Log epochs to experiment tracker
     - Support early stopping + gradient clipping

3. CELERY TASK (backend/app/tasks/training.py):
   - run_finetune_task(config) — Celery task wrapping the training service

4. API ROUTES (backend/app/api/routes/experiments.py + transfer.py):
   - GET /api/experiments — list experiments
   - POST /api/experiments — create experiment
   - GET /api/experiments/{id} — get with epochs
   - POST /api/experiments/{id}/epochs — log epoch
   - POST /api/transfer/start — start fine-tuning job

5. FRONTEND (frontend/src/app/(dashboard)/train/page.tsx — extend):
   - Experiment list with status indicators
   - Training curves chart (loss/accuracy per epoch) using a chart library
   - Experiment comparison table
   - Start training form: select backbone, dataset, hyperparameters

6. TESTS: test_create_experiment, test_log_epoch, test_best_checkpoint, test_finetune_config_validation

COMMIT with conventional commits. Add docs/experiment-tracker.md.
```

---

## WORKSTREAM 13 — Dataset Manager
**Branch:** `ai-feature/ws13-dataset-manager`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws13-dataset-manager.

YOUR TASK: Implement the Dataset Manager (M7).

Read CLAUDE.md for context. Then implement:

1. SERVICE (backend/app/services/data/dataset_manager.py):
   - DatasetService:
     - create_dataset(name, modality, workspace_id) → Dataset
     - upload_samples(dataset_id, files, labels=None) → upload count
     - list_datasets(workspace_id) → paginated list
     - get_dataset(dataset_id) → Dataset with stats
     - compute_stats(dataset_id) → class distribution, sample counts, size
     - split_dataset(dataset_id, train=0.7, val=0.15, test=0.15, stratified=True) → split info
     - delete_dataset(dataset_id) — soft delete
     - export_dataset(dataset_id, format='huggingface') → export path

2. STORAGE INTEGRATION (backend/app/services/data/storage.py):
   - MinIOStorageService:
     - upload_file(bucket, key, file_data) → url
     - download_file(bucket, key) → bytes
     - list_files(bucket, prefix) → file list
     - delete_file(bucket, key)

3. API ROUTES (backend/app/api/routes/datasets.py):
   - POST /api/datasets — create dataset
   - GET /api/datasets — list datasets
   - GET /api/datasets/{id} — get with stats
   - POST /api/datasets/{id}/upload — upload samples (multipart)
   - POST /api/datasets/{id}/split — trigger train/val/test split
   - GET /api/datasets/{id}/export — export dataset

4. FRONTEND (frontend/src/app/(dashboard)/train/page.tsx — add Dataset tab):
   - Dataset list with modality badges
   - Upload form with drag-and-drop
   - Dataset detail: sample preview grid, class distribution chart, split config
   - Split action with ratio sliders

5. TESTS: test_create_dataset, test_upload_samples, test_compute_stats, test_split_stratified, test_minio_upload_download

COMMIT with conventional commits. Add docs/dataset-manager.md.
```

---

## WORKSTREAM 14 — FAISS Cross-Modal Search
**Branch:** `ai-feature/ws14-faiss-search`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws14-faiss-search.

YOUR TASK: Implement FAISS-based cross-modal search (M13).

Read CLAUDE.md for domain context on FAISS, CLIP, cross-modal retrieval. Then implement:

1. EMBEDDING SERVICE (backend/app/services/search/embeddings.py):
   - EmbeddingService:
     - embed_image(image) → 512-dim vector (using CLIP ViT-B/32)
     - embed_text(text) → 512-dim vector (using CLIP text encoder)
     - embed_audio(audio, sr) → 512-dim vector (using CLAP or audio embedding model)
     - embed_batch(items, modality) → list of vectors

2. FAISS INDEX SERVICE (backend/app/services/search/faiss_index.py):
   - FAISSIndexService:
     - create_index(dimension=512, index_type='IVFFlat', nlist=100) → index
     - add_vectors(index, vectors, ids) → updated index
     - search(index, query_vector, k=10) → (distances, ids)
     - save_index(index, path), load_index(path) → index
     - get_index_stats(index) → {"total_vectors", "dimension", "index_type"}

3. SEARCH SERVICE (backend/app/services/search/search_service.py):
   - CrossModalSearchService:
     - index_asset(asset_id, modality, file_data) → embedding stored
     - search_by_text(query, k=10, modality_filter=None) → ranked results with scores
     - search_by_image(image, k=10) → ranked results
     - search_by_audio(audio, k=10) → ranked results
     - search_similar(asset_id, k=10) → find similar assets

4. API ROUTES (backend/app/api/routes/search.py):
   - POST /api/search/query — {"query": "text or base64", "modality": "text/image/audio", "k": 10, "filters": {}}
     - Return: ranked results with asset metadata, scores, thumbnails
   - POST /api/search/index — index an asset (called after upload)
   - GET /api/search/stats — index statistics

5. FRONTEND (frontend/src/app/(dashboard)/search/page.tsx):
   - Search bar with modality selector (text/image/audio)
   - Image upload for visual search
   - Results grid: thumbnail, title, score, modality badge
   - Filters: modality, date range, workspace

6. TESTS: test_clip_embedding_shape, test_faiss_add_and_search, test_cross_modal_text_to_image, test_api_search_endpoint

COMMIT with conventional commits. Add docs/faiss-search.md.
```

---

## WORKSTREAM 15 — Pipeline Builder
**Branch:** `ai-feature/ws15-pipeline-builder`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws15-pipeline-builder.

YOUR TASK: Implement the visual Pipeline Builder (M16).

Read CLAUDE.md for context. Then implement:

1. PIPELINE ENGINE (backend/app/services/pipeline/engine.py):
   - PipelineEngine:
     - validate_pipeline(definition) → validation result
     - execute_pipeline(pipeline_id) → PipelineRun (via Celery)
     - get_run_status(run_id) → status + results
   - Node types (20 core): input_image, input_audio, input_video, normalize, color_convert, detect_objects, optical_flow, frame_diff, stft, mel_spectrogram, mfcc, augment_audio, embed_clip, faiss_search, alert, webhook, transform, filter, merge, output

2. NODE REGISTRY (backend/app/services/pipeline/nodes.py):
   - BaseNode class with execute(inputs) → outputs interface
   - One class per node type inheriting BaseNode
   - Node metadata: name, category, inputs schema, outputs schema, icon

3. CELERY TASK (backend/app/tasks/pipeline.py):
   - run_pipeline_task(pipeline_id) — execute nodes in topological order

4. API ROUTES (backend/app/api/routes/pipeline.py):
   - POST /api/pipeline/create — save pipeline definition
   - GET /api/pipelines — list pipelines
   - GET /api/pipelines/{id} — get pipeline with definition
   - POST /api/pipeline/run/{id} — trigger execution
   - GET /api/pipeline/runs/{run_id} — get run status
   - GET /api/pipeline/nodes — list available node types with schemas

5. FRONTEND (frontend/src/app/(dashboard)/pipeline/page.tsx):
   - React Flow canvas with draggable nodes
   - Node palette sidebar (categorized: input, vision, audio, search, action)
   - Node configuration panel (click node → edit params)
   - Save pipeline, Run pipeline, View run history
   - frontend/src/components/pipeline/PipelineCanvas.tsx
   - frontend/src/components/pipeline/NodePalette.tsx
   - frontend/src/components/pipeline/NodeConfig.tsx

6. TESTS: test_pipeline_validation, test_node_execution, test_topological_sort, test_api_create_and_run

COMMIT with conventional commits. Add docs/pipeline-builder.md.
```

---

## WORKSTREAM 16 — Agentic Media Copilot
**Branch:** `ai-feature/ws16-copilot-agent`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws16-copilot-agent.

YOUR TASK: Implement the Agentic Media Copilot (Crown Jewel).

Read CLAUDE.md for context. Then implement:

1. COPILOT SERVICE (backend/app/services/agents/copilot.py):
   - CopilotService:
     - chat(message, context, workspace_id, agent_id) → streamed response
     - Integrate Anthropic Claude API (use anthropic Python SDK)
     - Build system prompt with: platform capabilities, current workspace context, recent events, memory
     - Stream tokens back via WebSocket or SSE
     - Tool use: give Claude tools for search, analyze_image, analyze_audio, create_alert, query_events

2. MEMORY SERVICE (backend/app/services/agents/memory.py):
   - AgentMemoryService:
     - store_memory(agent_id, content, importance_score) → AgentMemory
     - recall(agent_id, query, k=5) → relevant memories (by embedding similarity)
     - decay_memories(agent_id) — reduce freshness_score over time
     - promote_memory(memory_id, new_importance) — boost important memories
     - get_memory_summary(agent_id) → condensed memory overview

3. AGENT TOOLS (backend/app/services/agents/tools.py):
   - Define Claude-compatible tool schemas:
     - search_media(query, modality) — searches FAISS index
     - analyze_image(image_url) — runs vision analysis
     - analyze_audio(audio_url) — runs audio analysis
     - create_alert(severity, message) — creates alert
     - query_events(filters) — queries event log
     - get_recent_activity(hours=24) — recent workspace activity

4. WebSocket (backend/app/ws/copilot.py):
   - ws://api/agents/stream — streaming copilot responses

5. API ROUTE (backend/app/api/routes/agents.py):
   - POST /api/agents/chat — send message, get response (or stream via WS)
   - GET /api/agents/{id}/memory — get agent memories
   - DELETE /api/agents/{id}/memory/{mem_id} — delete memory

6. FRONTEND (frontend/src/app/(dashboard)/agents/page.tsx):
   - Chat interface with streaming response display
   - Message history with user/assistant bubbles
   - Memory viewer panel (sidebar showing stored memories)
   - Skill pack switcher (Investigator, QA, Compliance, etc.)
   - Evidence pinning: pin analysis results to conversation
   - frontend/src/components/agents/CopilotChat.tsx
   - frontend/src/components/agents/MemoryPanel.tsx
   - frontend/src/components/agents/SkillPackSwitcher.tsx

7. TESTS: test_copilot_builds_system_prompt, test_memory_store_recall, test_memory_decay, test_tool_schemas_valid, test_api_chat_endpoint

COMMIT with conventional commits. Add docs/copilot-agent.md.
```

---

## WORKSTREAM 17 — Audio Transform Studio
**Branch:** `ai-feature/ws17-transform-audio`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws17-transform-audio.

YOUR TASK: Implement the Audio Transform Studio (M4).

Read CLAUDE.md for context. Then implement:

1. SERVICE (backend/app/services/transform/audio_transform.py):
   - AudioTransformService:
     - denoise(audio, sr, method='spectral_gating') → cleaned audio
     - remove_silence(audio, sr, threshold_db=-40, min_silence_ms=500) → trimmed audio
     - pitch_shift(audio, sr, semitones) → shifted audio
     - time_stretch(audio, sr, rate) → stretched audio
     - normalize_loudness(audio, sr, target_lufs=-14) → normalized audio
     - apply_eq(audio, sr, preset='flat') → equalized audio (presets: flat, voice, music, podcast)
     - speech_enhance(audio, sr) → enhanced speech audio
     - apply_chain(audio, sr, steps) → audio processed through chain

2. API ROUTES (backend/app/api/routes/transform.py — create new):
   - POST /api/transform/audio — accept audio + transform config
     - Return: transformed audio (base64), before/after waveform comparison, processing_time

3. FRONTEND (frontend/src/app/(dashboard)/transform/page.tsx):
   - Audio upload + waveform preview
   - Transform chain builder: add denoise → pitch → normalize as steps
   - Before/after comparison player
   - Preset buttons: "Podcast Cleanup", "Voice Enhancement", "Music Master"
   - Download transformed audio

4. TESTS: test_denoise_reduces_noise, test_pitch_shift_accuracy, test_loudness_normalization, test_transform_chain, test_api_transform_endpoint

COMMIT with conventional commits. Add docs/audio-transform.md.
```

---

## WORKSTREAM 18 — Video Transform Studio
**Branch:** `ai-feature/ws18-transform-video`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws18-transform-video.

YOUR TASK: Implement the Video/Vision Transform Studio (M5).

Read CLAUDE.md for context. Then implement:

1. SERVICE (backend/app/services/transform/video_transform.py):
   - VideoTransformService:
     - remove_background(image) → image with transparent/replaced background (using rembg)
     - stabilize_video(frames) → stabilized frames (using optical flow-based stabilization)
     - super_resolution(image, scale=4) → upscaled image
     - style_transfer(image, style='monet') → stylized image
     - auto_crop(image, aspect_ratio='16:9') → cropped image
     - generate_thumbnail(video_path, method='keyframe') → thumbnail image
     - scene_detection(video_path) → list of scene cut timestamps

2. API ROUTES (backend/app/api/routes/transform.py — extend):
   - POST /api/transform/video/background-remove — image → transparent background
   - POST /api/transform/video/super-resolution — image → upscaled
   - POST /api/transform/video/thumbnail — video → thumbnail

3. FRONTEND (frontend/src/app/(dashboard)/transform/page.tsx — extend with Video tab):
   - Image upload for background removal
   - Before/after slider comparison
   - Super-resolution preview
   - Thumbnail generator from video

4. TESTS: test_background_removal, test_super_resolution_upscales, test_scene_detection, test_api_endpoints

COMMIT with conventional commits. Add docs/video-transform.md.
```

---

## WORKSTREAM 19 — Frontend Dashboard & UI Polish
**Branch:** `ai-feature/ws19-frontend-dashboard`
**Scope:** ui

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws19-frontend-dashboard.

YOUR TASK: Build the main dashboard, sidebar, and shared UI components.

Read CLAUDE.md for context. Then implement:

1. SHARED UI COMPONENTS (frontend/src/components/ui/):
   - Button.tsx — primary, secondary, danger, ghost variants + loading state
   - Card.tsx — container with header, body, footer slots
   - Badge.tsx — status badges (success/warning/error/info) + module badges
   - Modal.tsx — dialog overlay with title, body, actions
   - DataTable.tsx — sortable, filterable table with pagination
   - FileUpload.tsx — drag-and-drop zone with preview
   - Chart.tsx — wrapper around recharts for line/bar/pie/donut charts
   - Tabs.tsx — tab navigation component
   - Toast.tsx — notification toasts (success/error/warning)
   - LoadingSpinner.tsx — spinner + skeleton loaders
   - EmptyState.tsx — "no data" placeholder with icon + action

2. LAYOUT (frontend/src/app/(dashboard)/layout.tsx):
   - Collapsible sidebar with icons + labels (all 15 nav items)
   - Top bar with: workspace name, search shortcut, user menu, notifications bell
   - Breadcrumbs
   - Mobile responsive: sidebar becomes hamburger menu

3. DASHBOARD HOME (frontend/src/app/(dashboard)/page.tsx):
   - Stats cards row: Active Streams, Models in Production, Open Alerts, Assets Count
   - Recent activity feed (last 10 events)
   - Quick actions: Start Capture, Upload Media, Run Pipeline, Ask Copilot
   - System health indicator (green/yellow/red)
   - Module status grid: show which modules are active/available

4. SETTINGS PAGE (frontend/src/app/(dashboard)/settings/page.tsx):
   - Workspace settings form
   - API key management (create/revoke)
   - User management table (list, invite, change role)
   - Integration settings (placeholder)

5. AUTH PAGES:
   - frontend/src/app/login/page.tsx — login form
   - frontend/src/app/register/page.tsx — register form with workspace creation

6. PROVIDERS (frontend/src/components/providers.tsx):
   - QueryClientProvider, auth state check, toast provider

7. STYLES: Ensure consistent Tailwind theme (colors, spacing, typography)

COMMIT with conventional commits.
```

---

## WORKSTREAM 20 — End-to-End Testing & Integration
**Branch:** `ai-feature/ws20-testing-e2e`
**Scope:** fullstack

```
You are working on the VisionAudioForge project at this directory. You are on branch ai-feature/ws20-testing-e2e.

YOUR TASK: Create comprehensive end-to-end and integration tests.

Read CLAUDE.md for context. Then implement:

1. BACKEND INTEGRATION TESTS (backend/tests/integration/):
   - test_vision_pipeline_e2e.py:
     - Upload image → preprocess → detect → search → verify full flow
   - test_audio_pipeline_e2e.py:
     - Upload audio → analyze (STFT/MFCC) → augment → verify results
   - test_model_lifecycle_e2e.py:
     - Register model → create experiment → log epochs → promote → compare
   - test_search_e2e.py:
     - Upload image → index → text search → verify cross-modal match
   - test_pipeline_execution_e2e.py:
     - Create pipeline → run → verify results
   - test_auth_flow_e2e.py:
     - Register → login → access protected route → refresh → logout

2. TEST FIXTURES (backend/tests/fixtures/):
   - conftest.py: async test client, test database, test user, test workspace
   - Create sample test files: small test image (100x100 PNG), short audio file (1s WAV), sample pipeline definition JSON

3. API CONTRACT TESTS (backend/tests/api/):
   - Test every API endpoint returns correct status codes and response shapes
   - Test error cases return proper error format
   - Test pagination works correctly

4. TEST CONFIGURATION:
   - pytest.ini or pyproject.toml pytest config
   - Coverage configuration targeting 70%+ on services/
   - Makefile targets: test, test:unit, test:integration, test:coverage

5. CI CONFIG (.github/workflows/test.yml):
   - GitHub Actions workflow: install deps → lint → test → coverage report
   - Use PostgreSQL and Redis service containers
   - Cache pip dependencies

6. TEST UTILITIES (backend/tests/utils.py):
   - create_test_image(width, height, color) → numpy array
   - create_test_audio(duration, sr, frequency) → numpy array
   - create_test_user(client) → user + tokens
   - assert_response_shape(response, expected_keys)

COMMIT with conventional commits. Add docs/testing.md.
```

---

## Summary Table

| WS | Branch | Module | Scope | Dependencies |
|----|--------|--------|-------|-------------|
| 01 | ws01-docker-infra | Infrastructure | infra | none |
| 02 | ws02-database-migrations | DB Schema | api | none |
| 03 | ws03-auth-system | Auth/RBAC | api | none |
| 04 | ws04-health-observability | Health/Metrics | api | none |
| 05 | ws05-vision-preprocessing | M2 Vision | api | none |
| 06 | ws06-vision-optical-flow | M2 Motion | api | none |
| 07 | ws07-vision-detection | M2 Detection | api | none |
| 08 | ws08-audio-spectral | M3 Audio | api | none |
| 09 | ws09-audio-augmentation | M3 Augment | api | none |
| 10 | ws10-capture-engine | M1 Capture | fullstack | none |
| 11 | ws11-model-registry | M6 Registry | fullstack | none |
| 12 | ws12-experiment-tracker | M6 Training | fullstack | none |
| 13 | ws13-dataset-manager | M7 Data | fullstack | none |
| 14 | ws14-faiss-search | M13 Search | fullstack | none |
| 15 | ws15-pipeline-builder | M16 Pipeline | fullstack | none |
| 16 | ws16-copilot-agent | Copilot | fullstack | none |
| 17 | ws17-transform-audio | M4 Transform | fullstack | none |
| 18 | ws18-transform-video | M5 Transform | fullstack | none |
| 19 | ws19-frontend-dashboard | Dashboard UI | ui | none |
| 20 | ws20-testing-e2e | Testing | fullstack | none |

All workstreams build on the same scaffold commit and can run in parallel without conflicts because each touches distinct files/directories.
