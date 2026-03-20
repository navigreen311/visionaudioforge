# VAF API Reference

Complete API reference for all 327+ endpoints in VisionAudioForge.

**Base URL:** `http://localhost:8000`

**Interactive docs:** [Swagger UI](http://localhost:8000/docs) | [ReDoc](http://localhost:8000/redoc)

**Authentication:** Most endpoints require a Bearer token obtained via `/api/auth/login`. Pass it as `Authorization: Bearer <token>`.

---

## Table of Contents

1. [Health](#health)
2. [Metrics](#metrics)
3. [Auth](#auth)
4. [Vision](#vision)
5. [Audio](#audio)
6. [Transform](#transform)
7. [Transfer / Models](#transfer--models)
8. [Experiments](#experiments)
9. [Registry](#registry)
10. [Search](#search)
11. [Pipeline](#pipeline)
12. [Alerts](#alerts)
13. [Agents](#agents)
14. [Assets](#assets)
15. [Datasets](#datasets)
16. [Annotations](#annotations)
17. [Safety](#safety)
18. [Validation](#validation)
19. [Workspaces](#workspaces)
20. [Capture](#capture)
21. [Evaluation](#evaluation)
22. [Investigation](#investigation)
23. [Observability](#observability)
24. [Runtime](#runtime)
25. [Governance](#governance)
26. [Integrations](#integrations)
27. [Knowledge Graph](#knowledge-graph)
28. [Semantic Memory](#semantic-memory)
29. [Command Center](#command-center)
30. [Simulation](#simulation)
31. [ReviewOps](#reviewops)
32. [Edge](#edge)
33. [Edge Fleet](#edge-fleet)
34. [Verticals](#verticals)
35. [Federated](#federated)
36. [Mobile](#mobile)
37. [Plugins](#plugins)
38. [Developer](#developer)

---

## Health

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 1 | `GET` | `/api/health` | System health check with DB, Redis, MinIO probes | No | - | `HealthResponse` (status, version, services, uptime_seconds, timestamp) |

---

## Metrics

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 2 | `GET` | `/api/metrics` | Prometheus metrics endpoint | No | - | Prometheus text format |

---

## Auth

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 3 | `POST` | `/api/auth/register` | Create new user and workspace | No | `RegisterRequest` (email, password, workspace_name) | `AuthResponse` (access_token, refresh_token, user) |
| 4 | `POST` | `/api/auth/login` | Authenticate with email + password | No | `LoginRequest` (email, password) | `AuthResponse` (access_token, refresh_token, user) |
| 5 | `POST` | `/api/auth/refresh` | Exchange refresh token for new access token | No | `RefreshRequest` (refresh_token) | `TokenResponse` (access_token, refresh_token) |
| 6 | `GET` | `/api/auth/me` | Get currently authenticated user | Yes | - | `UserResponse` |
| 7 | `PUT` | `/api/auth/me` | Update current user email/password | Yes | `UpdateProfileRequest` (email?, password?) | `UserResponse` |
| 8 | `POST` | `/api/auth/logout` | Logout (placeholder) | No | - | `{message}` |

---

## Vision

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 9 | `POST` | `/api/vision/analyze` | Analyze image (stub, 501) | No | - | `{status, module}` |
| 10 | `POST` | `/api/vision/optical-flow` | Optical flow analysis (stub, 501) | No | - | `{status, module}` |
| 11 | `POST` | `/api/vision/frame-diff` | Frame differencing (stub, 501) | No | - | `{status, module}` |
| 12 | `POST` | `/api/vision/screen-analyze` | Screen analysis (stub, 501) | No | - | `{status, module}` |
| 13 | `POST` | `/api/vision/detect` | Detect objects in an image | No | `file` (multipart), `confidence` (float), `classes` (str) | `{detections, count, visualization, processing_time_ms}` |
| 14 | `POST` | `/api/vision/ocr` | Extract text from image via OCR | No | `file` (multipart) | `{full_text, blocks, processing_time_ms}` |
| 15 | `POST` | `/api/vision/error-analysis` | Classification error analysis | No | `ErrorAnalysisRequest` (predictions, ground_truth, classes) | Quality report dict |
| 16 | `POST` | `/api/vision/track` | Track objects across video frames | No | `files` (multipart list), `method` (sort\|centroid) | `{frames, trajectories, total_frames, processing_time_ms}` |
| 17 | `POST` | `/api/vision/segment` | Segment objects in image | No | `file` (multipart), `method` (semantic\|instance) | `{method, instances/classes, overlay, processing_time_ms}` |
| 18 | `POST` | `/api/vision/pose` | Estimate human pose keypoints | No | `file` (multipart) | `{poses, count, visualization, processing_time_ms}` |
| 19 | `POST` | `/api/vision/panoptic` | Panoptic segmentation (stuff + things) | No | `file` (multipart) | `{things, num_stuff_pixels, num_things, class_map, combined_mask, processing_time_ms}` |
| 20 | `POST` | `/api/vision/trajectory` | Analyze trajectory movement patterns | No | `TrajectoryRequest` (track_history) | Analysis dict |
| 21 | `POST` | `/api/vision/embeddings/visualize` | Reduce and visualize embeddings | No | `EmbeddingVisualizeRequest` (embeddings, labels?, method) | `{plot, method, num_points}` |

---

## Audio

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 22 | `POST` | `/api/audio/analyze` | Audio analysis (stub, 501) | No | - | `{status, module}` |
| 23 | `POST` | `/api/audio/augment` | Augment audio with pipeline or preset | No | `file` (multipart), `config` (form) | `AudioAugmentResponse` (augmented_audio b64, applied_augmentations, durations, processing_time_ms) |
| 24 | `POST` | `/api/audio/transcribe` | Speech-to-text via Whisper | No | `file` (multipart), `language` (form) | Transcription result |
| 25 | `POST` | `/api/audio/vad` | Voice activity detection | No | `file` (multipart) | `{segments, speech_ratio, duration_s}` |
| 26 | `POST` | `/api/audio/separate` | Source separation into stems | No | `file` (multipart), `stems` (form) | `{stems: {name: b64_wav}}` |
| 27 | `POST` | `/api/audio/classify` | Classify audio content | No | `file` (multipart) | Classification result |
| 28 | `POST` | `/api/audio/voiceprint` | Extract 128-dim voiceprint | No | `file` (multipart) | `{voiceprint, dimensions}` |
| 29 | `POST` | `/api/audio/voiceprint/compare` | Compare two voiceprints | No | `file1`, `file2` (multipart) | Comparison result |
| 30 | `POST` | `/api/audio/fingerprint` | Generate acoustic fingerprint | No | `file` (multipart) | `{fingerprint, duration_s, peaks}` |
| 31 | `POST` | `/api/audio/fingerprint/match` | Compare two audio fingerprints | No | `file1`, `file2` (multipart) | `{match, similarity, offset_s}` |
| 32 | `POST` | `/api/audio/av-sync` | Detect audio-video sync offset | No | `file` (multipart), `fps` (form) | Sync result |
| 33 | `POST` | `/api/audio/embed` | Generate 512-dim audio embedding | No | `file` (multipart), `model` (form) | `{embedding, dimensions, model}` |
| 34 | `POST` | `/api/audio/translate` | Translate speech in audio | No | `file` (multipart), `source_lang`, `target_lang` (form) | Translation result |

---

## Transform

### Audio Transforms

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 35 | `POST` | `/api/transform/audio/denoise` | Denoise audio file | No | `file` (multipart), `method` (form) | `{audio (b64), sample_rate, processing_time_ms}` |
| 36 | `POST` | `/api/transform/audio/silence-remove` | Remove silence from audio | No | `file` (multipart) | `{audio, sample_rate, original_duration_s, result_duration_s, processing_time_ms}` |
| 37 | `POST` | `/api/transform/audio/pitch-shift` | Pitch-shift audio | No | `file` (multipart), `semitones` (form) | `{audio, sample_rate, semitones, processing_time_ms}` |
| 38 | `POST` | `/api/transform/audio/time-stretch` | Time-stretch audio | No | `file` (multipart), `rate` (form) | `{audio, sample_rate, rate, original_duration_s, result_duration_s, processing_time_ms}` |
| 39 | `POST` | `/api/transform/audio/eq` | Apply EQ preset to audio | No | `file` (multipart), `preset` (form) | `{audio, sample_rate, preset, processing_time_ms}` |
| 40 | `POST` | `/api/transform/audio/chain` | Apply chain of audio transforms | No | `file` (multipart), `steps` (form JSON) | `{audio, sample_rate, applied, processing_time_ms}` |
| 41 | `POST` | `/api/transform/audio/voice-convert` | Voice conversion | No | `file` (multipart), `target_voice` (form) | `{audio, sample_rate, target_voice, processing_time_ms}` |
| 42 | `POST` | `/api/transform/audio/chapters` | Detect chapters via silences | No | `file` (multipart), `min_silence` (form) | `{chapters, total_chapters, duration_s, processing_time_ms}` |
| 43 | `POST` | `/api/transform/audio/noise-profile` | Analyze noise profile | No | `file` (multipart) | `{profile..., sample_rate, processing_time_ms}` |
| 44 | `GET` | `/api/transform/audio/voices` | List available TTS voices | No | - | `{voices}` |
| 45 | `GET` | `/api/transform/audio/compressor-presets` | List compressor presets | No | - | `{presets}` |
| 46 | `POST` | `/api/transform/audio/tts` | Text-to-speech synthesis | No | `text`, `voice`, `speed` (form) | `{audio, sample_rate, duration_s, voice, speed, processing_time_ms}` |
| 47 | `POST` | `/api/transform/audio/dub` | Auto-dub audio to target language | No | `file` (multipart), `source_lang`, `target_lang`, `voice` (form) | `{audio, original_transcript, translated_text, source_lang, target_lang, processing_time_ms}` |
| 48 | `POST` | `/api/transform/audio/dereverb` | Remove reverberation | No | `file` (multipart), `strength` (form) | `{audio, sample_rate, strength, duration_s, processing_time_ms}` |
| 49 | `POST` | `/api/transform/audio/compress` | Dynamic range compression | No | `file` (multipart), `threshold`, `ratio`, `preset` (form) | `{audio, sample_rate, preset, threshold_db, ratio, duration_s, processing_time_ms}` |

### Video / Image Transforms

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 50 | `POST` | `/api/transform/video/background-remove` | Remove background from image | No | `file` (multipart), `method` (form) | `{image (b64), method, processing_time_ms}` |
| 51 | `POST` | `/api/transform/video/super-resolution` | Upscale image | No | `file` (multipart), `scale` (form) | `{image, original_size, output_size, scale, processing_time_ms}` |
| 52 | `POST` | `/api/transform/video/style` | Apply style transfer | No | `file` (multipart), `style` (form) | `{image, style, processing_time_ms}` |
| 53 | `POST` | `/api/transform/video/auto-crop` | Auto-crop to target aspect ratio | No | `file` (multipart), `aspect` (form) | `{image, original_size, cropped_size}` |
| 54 | `POST` | `/api/transform/video/thumbnail` | Generate thumbnail from frames | No | `files` (multipart list), `method` (form) | `{thumbnail, frame_index}` |
| 55 | `POST` | `/api/transform/video/inpaint` | Inpaint masked image regions | No | `file`, `mask` (multipart) | `{image, processing_time_ms}` |
| 56 | `POST` | `/api/transform/video/color-grade` | Apply color grading preset | No | `file` (multipart), `preset` (form) | `{image, preset, processing_time_ms}` |
| 57 | `POST` | `/api/transform/video/subtitle` | Burn subtitle text onto image | No | `file` (multipart), `text`, `position` (form) | `{image, text, position, processing_time_ms}` |
| 58 | `POST` | `/api/transform/video/interpolate` | Generate intermediate frames | No | `frame1`, `frame2` (multipart), `count` (form) | `{frames, count, processing_time_ms}` |

---

## Transfer / Models

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 59 | `POST` | `/api/transfer/start` | Start a fine-tuning job | Yes | `FinetuneRequest` (backbone, dataset_path, num_epochs, learning_rate, batch_size, freeze_layers, num_classes, workspace_id, ...) | `FinetuneResponse` (job_id, experiment_id, status) |
| 60 | `POST` | `/api/transfer/automl/sweep` | Hyperparameter grid search | No | `SweepRequest` (base_config, param_grid, num_trials) | `{results}` |
| 61 | `POST` | `/api/transfer/automl/recommend-backbone` | Recommend backbone from dataset stats | No | `BackboneRequest` (dataset_stats) | Recommendation dict |
| 62 | `GET` | `/api/transfer/recipes` | List training recipe presets | No | - | `{recipes, details}` |
| 63 | `GET` | `/api/transfer/recipes/{use_case}` | Get specific training recipe | No | - | Recipe dict |
| 64 | `POST` | `/api/transfer/few-shot/build` | Build few-shot classifier | No | `FewShotBuildRequest` (examples: {class: [b64_images]}) | Classifier result |
| 65 | `POST` | `/api/transfer/few-shot/predict` | Predict with few-shot classifier | No | `file` (multipart), `classifier_id` | Prediction result |
| 66 | `POST` | `/api/transfer/zero-shot` | Zero-shot classify image | No | `ZeroShotRequest` (candidate_labels), `file` (multipart) | Classification result |
| 67 | `POST` | `/api/transfer/feedback` | Store prediction feedback | No | `FeedbackRequest` (model_id, predicted, corrected, input_data?, user_id?) | Feedback event |
| 68 | `GET` | `/api/transfer/feedback/{model_id}` | Get feedback queue for model | No | - | Feedback queue status |

---

## Experiments

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 69 | `GET` | `/api/experiments` | List experiments for workspace | Yes | Query: workspace_id, model_id?, skip, limit | `PaginatedResponse` |
| 70 | `POST` | `/api/experiments` | Create new experiment | Yes | `ExperimentCreate` (name, config, model_id?, workspace_id) | `ExperimentRead` |
| 71 | `GET` | `/api/experiments/{experiment_id}` | Get experiment with all epochs | Yes | - | `ExperimentRead` |
| 72 | `POST` | `/api/experiments/{experiment_id}/epochs` | Log epoch metrics | Yes | `EpochLog` (epoch, metrics) | `EpochRead` |
| 73 | `GET` | `/api/experiments/{experiment_id}/best` | Get best checkpoint by metric | Yes | Query: metric, mode | Best checkpoint dict |
| 74 | `POST` | `/api/experiments/compare` | Compare multiple experiments | Yes | `ExperimentCompareRequest` (experiment_ids) | Comparison list |

---

## Registry

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 75 | `POST` | `/api/registry/register` | Register a model | Yes | `ModelCreate` (name, version, backbone, metrics, workspace_id) | `ModelRead` |
| 76 | `GET` | `/api/registry/models` | List models for workspace | Yes | Query: workspace_id, status?, skip, limit | `PaginatedResponse` |
| 77 | `GET` | `/api/registry/models/{model_id}` | Get model details | Yes | - | `ModelRead` |
| 78 | `PUT` | `/api/registry/models/{model_id}/status` | Update model status | Yes | `StatusUpdate` (status) | `ModelRead` |
| 79 | `POST` | `/api/registry/compare` | Compare two models | Yes | `CompareRequest` (model_a_id, model_b_id) | Comparison result |
| 80 | `POST` | `/api/registry/models/{model_id}/rollback` | Rollback model to version | Yes | `RollbackRequest` (to_version) | `ModelRead` |

---

## Search

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 81 | `POST` | `/api/search/query` | Search by text query (CLIP embeddings + FAISS) | No | `SearchQueryRequest` (query, modality, k, filters) | `SearchResponse` (results, total_results, processing_time_ms) |
| 82 | `POST` | `/api/search/query/upload` | Search by image upload | No | `file` (multipart), `k` | `SearchResponse` |
| 83 | `POST` | `/api/search/index` | Index an asset into FAISS | No | `IndexAssetRequest` (asset_id) | `IndexResponse` (asset_id, indexed, embedding_dim) |
| 84 | `GET` | `/api/search/stats` | FAISS index statistics | No | - | `StatsResponse` (total_vectors, dimension, index_type) |
| 85 | `POST` | `/api/search/similar/{asset_id}` | Find similar assets | No | Query: k | `SearchResponse` |
| 86 | `POST` | `/api/search/audio-query` | Search by audio (CLAP embeddings) | No | `file` (multipart), `k` | `SearchResponse` |
| 87 | `POST` | `/api/search/voice` | Voice query (STT then text search) | No | `file` (multipart) | `{transcript, search_results}` |
| 88 | `POST` | `/api/search/fuse` | Build fused multimodal timeline | No | `FuseRequest` (workspace_id, start, end) | `{timeline}` |
| 89 | `POST` | `/api/search/saved` | Save a search | No | `SaveSearchRequest` (workspace_id, user_id, name, query, modality, filters) | Saved search dict |
| 90 | `GET` | `/api/search/saved` | List saved searches | No | Query: workspace_id, user_id? | `{saved_searches}` |
| 91 | `POST` | `/api/search/saved/{search_id}/execute` | Re-run a saved search | No | - | `{results}` |
| 92 | `POST` | `/api/search/conversational` | Conversational search with context | No | `ConversationalRequest` (query, history, workspace_id) | Conversational result |

---

## Pipeline

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 93 | `GET` | `/api/pipeline/nodes` | List registered node types | No | - | `list[NodeTypeInfo]` |
| 94 | `POST` | `/api/pipeline/validate` | Validate pipeline definition | No | `PipelineValidate` (definition) | `ValidationResult` |
| 95 | `POST` | `/api/pipeline/create` | Create a new pipeline | Yes | `PipelineCreate` (name, description, definition, workspace_id) | `PipelineRead` |
| 96 | `GET` | `/api/pipelines` | List pipelines | Yes | Query: workspace_id?, page, page_size | `PaginatedResponse` |
| 97 | `GET` | `/api/pipelines/{pipeline_id}` | Get pipeline by ID | Yes | - | `PipelineRead` |
| 98 | `POST` | `/api/pipeline/run/{pipeline_id}` | Start a pipeline run (Celery) | Yes | - | `PipelineRunStart` (run_id, status) |
| 99 | `GET` | `/api/pipeline/runs/{run_id}` | Get pipeline run status | Yes | - | `PipelineRunRead` |
| 100 | `POST` | `/api/pipeline/generate` | Generate pipeline from NL description | No | `GenerateRequest` (description) | `{definition, description}` |
| 101 | `GET` | `/api/pipeline/templates` | List all pipeline templates | No | - | Template list |
| 102 | `GET` | `/api/pipeline/templates/{name}` | Get specific template | No | - | Template dict |
| 103 | `POST` | `/api/pipeline/schedule` | Create cron schedule for pipeline | No | `ScheduleRequest` (pipeline_id, cron) | Schedule result |
| 104 | `GET` | `/api/pipeline/schedules` | List active schedules | No | Query: workspace_id? | Schedule list |
| 105 | `POST` | `/api/pipeline/suggest-next` | Suggest next nodes for pipeline | No | `SuggestNextRequest` (current_nodes) | `{suggestions}` |

---

## Alerts

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 106 | `POST` | `/api/alerts/rules` | Create alert rule | Yes | `AlertRuleCreate` (name, conditions, actions, enabled), Query: workspace_id | `AlertRuleRead` |
| 107 | `GET` | `/api/alerts/rules` | List alert rules | Yes | Query: workspace_id, enabled? | `list[AlertRuleRead]` |
| 108 | `GET` | `/api/alerts/rules/{rule_id}` | Get alert rule | Yes | - | `AlertRuleRead` |
| 109 | `PUT` | `/api/alerts/rules/{rule_id}` | Update alert rule | Yes | `AlertRuleUpdate` | `AlertRuleRead` |
| 110 | `DELETE` | `/api/alerts/rules/{rule_id}` | Soft-delete alert rule | Yes | - | `AlertRuleRead` |
| 111 | `GET` | `/api/alerts` | List alerts with filters | Yes | Query: workspace_id, status?, severity?, skip, limit | Paginated alerts |
| 112 | `GET` | `/api/alerts/stats` | Alert statistics | Yes | Query: workspace_id | `AlertStats` |
| 113 | `POST` | `/api/alerts/{alert_id}/acknowledge` | Acknowledge an alert | Yes | Query: user_id | `AlertRead` |
| 114 | `POST` | `/api/alerts/{alert_id}/resolve` | Resolve an alert | Yes | Query: user_id | `AlertRead` |
| 115 | `POST` | `/api/alerts/{alert_id}/dismiss` | Dismiss an alert | Yes | Query: user_id | `AlertRead` |
| 116 | `POST` | `/api/alerts/test` | Trigger a test alert | Yes | Query: rule_id, workspace_id | `AlertRead` |
| 117 | `GET` | `/api/alerts/incidents` | List incidents (grouped alerts) | Yes | Query: workspace_id, window_minutes | `{incidents, total}` |
| 118 | `GET` | `/api/alerts/incidents/{incident_id}/timeline` | Incident timeline | Yes | Query: workspace_id | `{incident_id, timeline}` |
| 119 | `GET` | `/api/alerts/incidents/{incident_id}/bundle` | Get/create evidence bundle | Yes | - | Evidence bundle dict |
| 120 | `POST` | `/api/alerts/{alert_id}/auto-clip` | Auto-clip capture for alert | Yes | Query: before_s, after_s | `{clip, snapshot}` |
| 121 | `POST` | `/api/alerts/{alert_id}/bundle` | Create evidence bundle | Yes | Query: case_id? | Evidence bundle dict |
| 122 | `GET` | `/api/alerts/{alert_id}/custody` | Chain of custody for alert evidence | Yes | - | Custody report |

---

## Agents

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 123 | `POST` | `/api/agents/chat` | Chat with copilot agent | Yes | `ChatRequest` (message, agent_id?, skill_pack, context?) | `ChatResponse` (response, agent_id, memories_used) |
| 124 | `GET` | `/api/agents` | List all agents | Yes | - | Agent list |
| 125 | `POST` | `/api/agents` | Create a new agent | Yes | `CreateAgentRequest` (name, agent_type, workspace_id?) | Agent dict |
| 126 | `GET` | `/api/agents/{agent_id}/memory` | List agent memories | Yes | - | Memory list |
| 127 | `POST` | `/api/agents/{agent_id}/memory/decay` | Trigger memory decay | Yes | - | `{agent_id, memories_decayed}` |
| 128 | `DELETE` | `/api/agents/{agent_id}/memory/{memory_id}` | Delete a memory | Yes | - | `{deleted, memory_id}` |
| 129 | `GET` | `/api/agents/{agent_id}/history` | Get conversation history | Yes | Query: limit | `{agent_id, messages, count}` |
| 130 | `DELETE` | `/api/agents/{agent_id}/history` | Clear conversation history | Yes | - | `{agent_id, deleted_count}` |
| 131 | `POST` | `/api/agents/{agent_id}/patrol/start` | Start autonomous patrol | Yes | - | `{agent_id, status}` |
| 132 | `POST` | `/api/agents/{agent_id}/patrol/stop` | Stop autonomous patrol | No | - | `{agent_id, status}` |
| 133 | `GET` | `/api/agents/{agent_id}/patrol/report` | Get patrol findings | Yes | Query: hours | Patrol report |

---

## Assets

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 134 | `POST` | `/api/assets/upload` | Upload one or more files | Yes | `file` (multipart list), `asset_type`, `workspace_id`, `tags?` (form) | `AssetUploadResponse` or `BulkUploadResponse` |
| 135 | `GET` | `/api/assets` | List assets with filters | Yes | Query: workspace_id, type?, tags?, skip, limit | `PaginatedResponse` |
| 136 | `GET` | `/api/assets/{asset_id}` | Get asset metadata | Yes | - | `AssetRead` |
| 137 | `PUT` | `/api/assets/{asset_id}` | Update asset tags/metadata | Yes | `AssetUpdate` (tags?, metadata?) | `AssetRead` |
| 138 | `DELETE` | `/api/assets/{asset_id}` | Soft-delete asset | Yes | - | `AssetRead` |
| 139 | `GET` | `/api/assets/{asset_id}/download` | Download raw file | Yes | - | Binary file stream |

---

## Datasets

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 140 | `POST` | `/api/datasets` | Create dataset | Yes | `DatasetCreate` (name, modality, workspace_id) | `DatasetRead` |
| 141 | `GET` | `/api/datasets` | List datasets | Yes | Query: workspace_id, skip, limit | `PaginatedResponse` |
| 142 | `GET` | `/api/datasets/{dataset_id}` | Get dataset details | Yes | - | `DatasetRead` |
| 143 | `POST` | `/api/datasets/{dataset_id}/upload` | Upload samples to dataset | Yes | `files` (multipart), `labels?` (form JSON) | `UploadSummary` |
| 144 | `POST` | `/api/datasets/{dataset_id}/split` | Split dataset (train/val/test) | Yes | `SplitRequest` (train, val, test, stratified) | `SplitResponse` |
| 145 | `POST` | `/api/datasets/{dataset_id}/stats` | Compute dataset statistics | Yes | - | Stats dict |
| 146 | `GET` | `/api/datasets/{dataset_id}/export` | Export dataset | Yes | Query: format | File download |
| 147 | `POST` | `/api/datasets/{dataset_id}/auto-label` | Auto-label unlabeled assets | Yes | `{model_name?, confidence_threshold?}` | Labeling result |
| 148 | `GET` | `/api/datasets/{dataset_id}/quality` | Dataset quality report | Yes | - | Quality report |
| 149 | `POST` | `/api/datasets/{dataset_id}/duplicates` | Find near-duplicate samples | Yes | - | Duplicate list |
| 150 | `POST` | `/api/datasets/{dataset_id}/dedup` | Remove duplicates | Yes | - | `{removed}` |
| 151 | `POST` | `/api/datasets/{dataset_id}/active-learning` | Create active-learning review queue | Yes | `{strategy?, k?}` | Queue result |
| 152 | `POST` | `/api/datasets/{dataset_id}/synthetic` | Generate synthetic samples | Yes | `{num?, pattern?}` | `{generated, pattern}` |

---

## Annotations

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 153 | `POST` | `/api/annotations` | Create annotation for asset | Yes | `AnnotationCreate` (asset_id, annotation_type, data, user_id, dataset_id?) | `AnnotationRead` |
| 154 | `GET` | `/api/annotations` | Get annotations for asset | Yes | Query: asset_id | `list[AnnotationRead]` |
| 155 | `PUT` | `/api/annotations/{annotation_id}` | Update annotation data | Yes | `AnnotationUpdate` (data) | `AnnotationRead` |
| 156 | `DELETE` | `/api/annotations/{annotation_id}` | Delete annotation | Yes | - | `{deleted}` |
| 157 | `GET` | `/api/datasets/{dataset_id}/annotations` | Get dataset annotations | Yes | - | `list[AnnotationRead]` |
| 158 | `POST` | `/api/datasets/{dataset_id}/annotations/export` | Export in COCO/YOLO/VOC | Yes | Query: format | Export data |
| 159 | `POST` | `/api/datasets/{dataset_id}/annotations/import` | Import annotations | Yes | `AnnotationImport` (data, format) | Import result |
| 160 | `GET` | `/api/datasets/{dataset_id}/annotations/stats` | Annotation statistics | Yes | - | `AnnotationStatsResponse` |

---

## Safety

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 161 | `POST` | `/api/safety/scan` | Scan file or text for safety/privacy | No | `file?` (multipart), `scan_type` (image\|text\|audio), `text?` (form) | `SafetyScanResult` |
| 162 | `POST` | `/api/safety/blur-faces` | Detect and blur faces | No | `file` (multipart) | `{image (b64)}` |
| 163 | `POST` | `/api/safety/redact` | Redact PII from text | No | `RedactRequest` (text) | `RedactionResult` |
| 164 | `POST` | `/api/safety/watermark` | Add text watermark to image | No | `file` (multipart), `text` (form) | `{image (b64)}` |
| 165 | `POST` | `/api/safety/report` | Aggregated safety report | No | `ReportRequest` (scan_ids) | `SafetyReport` |
| 166 | `POST` | `/api/safety/blur-plates` | Blur license plates | No | `file` (multipart) | `{image (b64)}` |
| 167 | `POST` | `/api/safety/anonymize-voice` | Anonymize voice in audio | No | `file` (multipart), `method` (form) | `{audio (b64)}` |
| 168 | `POST` | `/api/safety/policy/evaluate` | Evaluate scan against policy | No | `PolicyEvaluateRequest` (scan_result, policy_name) | Evaluation result |
| 169 | `POST` | `/api/safety/policy/check-export` | Check export allowed by policy | No | `ExportCheckRequest` (asset_id, policy) | Check result |
| 170 | `GET` | `/api/safety/compliance/{pack}` | Check compliance (hipaa/gdpr/soc2) | No | - | Compliance result |
| 171 | `POST` | `/api/safety/compliance/{pack}/report` | Generate compliance report | No | - | Compliance report |
| 172 | `POST` | `/api/safety/legal-hold` | Place legal hold on assets | No | `LegalHoldRequest` (asset_ids, reason) | Hold result |
| 173 | `GET` | `/api/safety/provenance/{asset_id}` | Get asset provenance chain | No | - | `{asset_id, chain}` |

---

## Validation

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 174 | `POST` | `/api/validate/calibration` | Calibration analysis (ECE, MCE) | No | `CalibrationRequest` (predictions, ground_truth, n_bins) | Calibration result |
| 175 | `POST` | `/api/validate/drift` | Data drift detection | No | `DriftRequest` (reference_stats, current_stats) | Drift result |
| 176 | `POST` | `/api/validate/uncertainty` | Prediction uncertainty (entropy) | No | `UncertaintyRequest` (predictions) | Uncertainty result |
| 177 | `GET` | `/api/validate/model-card/{model_id}` | Generate model card (stub, 501) | No | - | Stub response |
| 178 | `GET` | `/api/validate/audit/{model_id}` | Model audit trail (stub, 501) | No | - | Stub response |
| 179 | `POST` | `/api/validate/explain` | Saliency-map explainability | No | `file` (multipart), `model_output` (form) | `{saliency_map_base64, shape}` |

---

## Workspaces

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 180 | `GET` | `/api/workspaces` | List user workspaces | Yes | - | `list[WorkspaceRead]` |
| 181 | `POST` | `/api/workspaces` | Create workspace | Yes | `WorkspaceCreate` (name) | `WorkspaceRead` |
| 182 | `GET` | `/api/workspaces/{workspace_id}` | Get workspace details + stats | Yes | - | `WorkspaceDetail` |
| 183 | `PUT` | `/api/workspaces/{workspace_id}` | Update workspace (admin) | Yes (admin) | `WorkspaceUpdate` (name?, settings?) | `WorkspaceRead` |
| 184 | `GET` | `/api/workspaces/{workspace_id}/members` | List workspace members | Yes | - | `list[MemberRead]` |
| 185 | `POST` | `/api/workspaces/{workspace_id}/members` | Invite member (admin) | Yes (admin) | `MemberInvite` (email, role) | `MemberRead` |
| 186 | `PUT` | `/api/workspaces/{workspace_id}/members/{user_id}` | Change member role (admin) | Yes (admin) | `MemberRoleUpdate` (role) | `MemberRead` |
| 187 | `DELETE` | `/api/workspaces/{workspace_id}/members/{user_id}` | Remove member (admin) | Yes (admin) | - | 204 No Content |

---

## Capture

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 188 | `POST` | `/api/capture/rtsp` | Connect to RTSP stream | No | `RTSPConnectRequest` (url) | Stream info |
| 189 | `POST` | `/api/capture/sources` | Add capture source | No | `AddSourceRequest` (workspace_id, source_type, config?) | `{source_id}` |
| 190 | `GET` | `/api/capture/sources` | List capture sources | No | Query: workspace_id | `{sources}` |
| 191 | `POST` | `/api/capture/sources/{source_id}/switch` | Switch active capture source | No | `SwitchSourceRequest` (workspace_id) | `{active_source_id}` |
| 192 | `GET` | `/api/capture/sources/grid` | Get multi-cam grid layout | No | Query: workspace_id | Layout dict |
| 193 | `POST` | `/api/capture/record/start` | Start recording | No | `RecordStartRequest` (session_id, fps) | Recording result |
| 194 | `POST` | `/api/capture/record/stop` | Stop recording | No | `RecordStopRequest` (recording_id) | Clip info |
| 195 | `POST` | `/api/capture/snapshot` | Capture single frame snapshot | No | `SnapshotRequest` (session_id) | Snapshot result |

---

## Evaluation

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 196 | `POST` | `/api/evaluation/benchmarks` | Create benchmark configuration | Yes | `BenchmarkCreate` (name, dataset_id, model_ids, metrics, workspace_id) | `BenchmarkOut` |
| 197 | `POST` | `/api/evaluation/benchmarks/{benchmark_id}/run` | Run benchmark | Yes | - | `BenchmarkRunOut` (results, ranking, duration_ms) |
| 198 | `POST` | `/api/evaluation/tournament` | Round-robin model tournament | Yes | `TournamentRequest` (model_ids, dataset_id) | `TournamentOut` (matchups, rankings, overall_winner, wins) |
| 199 | `POST` | `/api/evaluation/threshold-analysis` | Threshold analysis (precision/recall/F1) | No | `ThresholdRequest` (predictions, ground_truth, thresholds?) | `list[ThresholdPoint]` |
| 200 | `GET` | `/api/evaluation/scorecard/{model_id}` | Generate model scorecard | Yes | - | `ScorecardOut` |

---

## Investigation

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 201 | `POST` | `/api/investigate/cases` | Create investigation case | Yes | `CreateCaseRequest` (name, description, workspace_id) | Event dict |
| 202 | `GET` | `/api/investigate/cases` | List cases in workspace | Yes | Query: workspace_id | Case list |
| 203 | `GET` | `/api/investigate/cases/{case_id}` | Get case with evidence and notes | Yes | - | `{case, events, evidence, notes}` |
| 204 | `POST` | `/api/investigate/cases/{case_id}/evidence` | Add evidence to case | Yes | `AddEvidenceRequest` (asset_id, notes, timestamp?) | Event dict |
| 205 | `POST` | `/api/investigate/cases/{case_id}/notes` | Add note to case | Yes | `AddNoteRequest` (user_id, content) | Event dict |
| 206 | `GET` | `/api/investigate/timeline` | Query events timeline | Yes | Query: workspace_id, start, end, types? | Event list |
| 207 | `GET` | `/api/investigate/cases/{case_id}/export` | Export case as JSON | Yes | - | Exported case |
| 208 | `POST` | `/api/investigate/cases/{case_id}/comments` | Add threaded comment | Yes | `AddCommentRequest` (user_id, content, parent_id?) | Event dict |
| 209 | `GET` | `/api/investigate/cases/{case_id}/comments` | Get threaded comments | Yes | - | Comment tree |
| 210 | `POST` | `/api/investigate/cases/{case_id}/checkpoint` | Create review checkpoint | Yes | `CreateCheckpointRequest` (user_id, title, description) | Event dict |
| 211 | `POST` | `/api/investigate/cases/{case_id}/approval` | Request approval | Yes | `CreateApprovalRequest` (user_id, approver_id, reason) | Event dict |
| 212 | `POST` | `/api/investigate/approvals/{approval_id}/process` | Process approval | Yes | `ProcessApprovalRequest` (user_id, decision, notes?) | Event dict |
| 213 | `GET` | `/api/investigate/approvals` | Get pending approval queue | Yes | Query: workspace_id, user_id? | Approval queue |
| 214 | `POST` | `/api/investigate/cases/{case_id}/report` | Generate draft report | Yes | - | Report dict |
| 215 | `POST` | `/api/investigate/cases/{case_id}/report/export` | Export report | Yes | `ExportReportRequest` (format) | `{content, format}` |
| 216 | `POST` | `/api/investigate/cases/{case_id}/report/sign` | Sign report (audit hash) | Yes | `SignReportRequest` (user_id) | Signature record |

---

## Observability

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 217 | `GET` | `/api/observability/dashboard` | System health overview | Yes | - | System overview dict |
| 218 | `GET` | `/api/observability/pipeline-health` | Pipeline execution metrics | Yes | - | Pipeline health dict |
| 219 | `GET` | `/api/observability/inference` | ML inference metrics | No | - | Inference metrics |
| 220 | `GET` | `/api/observability/errors` | Categorised error breakdown | Yes | Query: hours | Error taxonomy |
| 221 | `GET` | `/api/observability/queues` | Task-queue metrics | No | - | Queue metrics |
| 222 | `GET` | `/api/observability/sla` | SLA compliance check | Yes | Query: tier, period_hours | SLA compliance result |
| 223 | `POST` | `/api/observability/sla/report` | Generate SLA report | Yes | Query: period | SLA report |
| 224 | `GET` | `/api/observability/alert-fatigue` | Alert fatigue analysis | Yes | Query: workspace_id, days | Fatigue analysis |

---

## Runtime

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 225 | `GET` | `/api/runtime/gpu` | GPU device status | No | - | `{devices}` |
| 226 | `POST` | `/api/runtime/route` | Select best model for request | No | `RouteRequest` (request_type, constraints?) | Routing result |
| 227 | `GET` | `/api/runtime/cost/{workspace_id}` | Get cost report | No | Query: period | Cost report |
| 228 | `GET` | `/api/runtime/quota/{workspace_id}` | Get quota status | No | - | Quota status |
| 229 | `POST` | `/api/runtime/quota` | Set daily inference quota | No | `QuotaSetRequest` (workspace_id, daily_limit) | `{workspace_id, daily_limit, status}` |
| 230 | `GET` | `/api/runtime/cache/stats` | Inference cache statistics | No | - | Cache stats |
| 231 | `POST` | `/api/runtime/cache/clear` | Clear inference cache | No | Query: model_id? | `{cleared}` |
| 232 | `GET` | `/api/runtime/schedule` | Current job queue | No | - | `{queue, total_jobs}` |

---

## Governance

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 233 | `POST` | `/governance/api-keys` | Create API key | Yes | `CreateAPIKeyRequest` (name, scopes, expires_in_days?) | API key result |
| 234 | `GET` | `/governance/api-keys` | List workspace API keys | Yes | - | Key list (prefix only) |
| 235 | `DELETE` | `/governance/api-keys/{key_id}` | Revoke API key | Yes | - | `{revoked}` |
| 236 | `POST` | `/governance/api-keys/{key_id}/rotate` | Rotate API key | Yes | - | New key result |
| 237 | `GET` | `/governance/sso/config` | Get SSO configuration | Yes | - | SSO config |
| 238 | `POST` | `/governance/sso/login` | Initiate SSO login | No | `SSOLoginRequest` (workspace_id) | SSO login URL |
| 239 | `GET` | `/governance/permissions/{role}` | Get role permissions | No | - | `{role, permissions}` |
| 240 | `GET` | `/governance/billing/usage` | Get workspace usage | Yes | - | Usage data |
| 241 | `GET` | `/governance/billing/dashboard` | Billing dashboard | Yes | - | Billing dashboard |
| 242 | `POST` | `/governance/billing/upgrade` | Upgrade workspace plan | Yes | `UpgradePlanRequest` (plan) | Upgrade result |
| 243 | `GET` | `/governance/features` | Get enabled feature flags | Yes | - | `{plan, features}` |

---

## Integrations

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 244 | `POST` | `/api/integrations/slack/send` | Send Slack message via webhook | No | `SlackSendBody` (webhook_url, message, blocks?, channel?) | Send result |
| 245 | `POST` | `/api/integrations/teams/send` | Send Teams message via webhook | No | `TeamsSendBody` (webhook_url, message, card?) | Send result |
| 246 | `POST` | `/api/integrations/email/send` | Send email | No | `EmailSendBody` (to, subject, body, body_text?, from_addr?) | Send result |
| 247 | `POST` | `/api/integrations/webhooks` | Register outbound webhook | No | `WebhookRegisterBody` (workspace_id, name, url, events, secret?, headers?) | Webhook dict |
| 248 | `GET` | `/api/integrations/webhooks` | List workspace webhooks | No | Query: workspace_id | Webhook list |
| 249 | `DELETE` | `/api/integrations/webhooks/{webhook_id}` | Delete webhook | No | - | `{deleted}` |
| 250 | `POST` | `/api/integrations/webhooks/{webhook_id}/test` | Test webhook delivery | No | - | Test result |
| 251 | `POST` | `/api/integrations/storage/test` | Test storage connector | No | `StorageTestBody` (connector_type, config) | `{ok, connector_type}` |
| 252 | `GET` | `/api/integrations/events` | List recent event bus events | No | Query: limit | Event list |

---

## Knowledge Graph

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 253 | `POST` | `/api/knowledge-graph/nodes` | Add node to graph | No | `NodeCreate` (label, node_type, properties, workspace_id?) | Node dict |
| 254 | `GET` | `/api/knowledge-graph/nodes` | List all nodes | No | Query: limit | Node list |
| 255 | `GET` | `/api/knowledge-graph/nodes/{node_id}` | Get single node | No | - | Node dict |
| 256 | `POST` | `/api/knowledge-graph/edges` | Add edge between nodes | No | `EdgeCreate` (source_id, target_id, relation, weight, properties) | Edge dict |
| 257 | `GET` | `/api/knowledge-graph/edges` | List all edges | No | - | Edge list |
| 258 | `GET` | `/api/knowledge-graph/nodes/{node_id}/neighbors` | Get node neighbors | No | - | `{node_id, neighbors}` |
| 259 | `POST` | `/api/knowledge-graph/scene-extract` | Extract entities from description | No | `SceneExtractRequest` (description, workspace_id?) | `{description, entities_extracted, entities, relations}` |

---

## Semantic Memory

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 260 | `POST` | `/api/semantic-memory/store` | Store a semantic memory | No | `MemoryStore` (content, category, importance, metadata, workspace_id?) | Memory dict |
| 261 | `POST` | `/api/semantic-memory/recall` | Recall memories matching query | No | `MemoryRecallRequest` (query, limit, category?) | `{query, results, total}` |
| 262 | `POST` | `/api/semantic-memory/decay` | Apply time-based decay | No | Query: threshold, factor | `{decayed_count, factor}` |
| 263 | `POST` | `/api/semantic-memory/promote/{memory_id}` | Boost memory importance | No | Query: boost | Memory dict |
| 264 | `GET` | `/api/semantic-memory/memories` | List all memories | No | Query: limit | Memory list |

---

## Command Center

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 265 | `POST` | `/api/command-center/streams` | Add video stream | No | `StreamCreate` (name, source_url, stream_type, workspace_id?) | Stream dict |
| 266 | `GET` | `/api/command-center/streams` | List all streams | No | - | Stream list |
| 267 | `POST` | `/api/command-center/layout` | Set grid layout | No | `LayoutSet` (name, grid, columns, rows) | Layout dict |
| 268 | `GET` | `/api/command-center/layout` | Get current layout | No | - | Layout dict |
| 269 | `POST` | `/api/command-center/shifts` | Create operator shift | No | `ShiftCreate` (operator_id, start_time, end_time, zone?) | Shift dict |
| 270 | `GET` | `/api/command-center/shifts` | List shifts | No | - | Shift list |
| 271 | `GET` | `/api/command-center/dashboard` | Command center dashboard | No | - | `{total_streams, active_streams, current_layout, active_shifts, status}` |

---

## Simulation

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 272 | `POST` | `/api/simulation/scenarios` | Generate test scenario | No | `ScenarioGenerate` (name, scenario_type, parameters, workspace_id?) | Scenario dict |
| 273 | `GET` | `/api/simulation/scenarios` | List scenarios | No | - | Scenario list |
| 274 | `GET` | `/api/simulation/scenarios/{scenario_id}` | Get scenario details | No | - | Scenario dict |
| 275 | `POST` | `/api/simulation/run` | Run simulation | No | `SimulationRun` (scenario_id, config) | Simulation result (throughput, latency, error_rate) |
| 276 | `GET` | `/api/simulation/report/{simulation_id}` | Get simulation report | No | - | `{simulation_id, scenario, status, results, summary}` |

---

## ReviewOps

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 277 | `POST` | `/api/reviewops/tasks` | Create review task | No | `TaskCreate` (title, description, asset_ids, workspace_id?) | Task dict |
| 278 | `GET` | `/api/reviewops/tasks` | List review tasks | No | Query: status? | Task list |
| 279 | `GET` | `/api/reviewops/tasks/{task_id}` | Get task details | No | - | Task dict |
| 280 | `POST` | `/api/reviewops/tasks/{task_id}/assign` | Assign reviewer | No | `TaskAssign` (reviewer_id) | Task dict |
| 281 | `POST` | `/api/reviewops/tasks/{task_id}/review` | Submit review | No | `ReviewSubmit` (verdict, comments, annotations) | Task dict |
| 282 | `GET` | `/api/reviewops/tasks/{task_id}/status` | Check task status | No | - | `{task_id, status, completed}` |

---

## Edge

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 283 | `POST` | `/api/edge/export` | Export model to edge format | No | `ExportRequest` (model_id, format, optimize, quantize) | Export dict |
| 284 | `GET` | `/api/edge/exports` | List exports | No | Query: model_id? | Export list |
| 285 | `GET` | `/api/edge/exports/{export_id}` | Get export details | No | - | Export dict |
| 286 | `GET` | `/api/edge/formats` | List supported export formats | No | - | Format list (onnx, tensorrt, tflite, coreml, openvino) |

---

## Edge Fleet

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 287 | `POST` | `/api/fleet/devices` | Register edge device | No | `DeviceRegister` (name, device_type, capabilities, location?) | Device dict |
| 288 | `GET` | `/api/fleet/devices` | List registered devices | No | - | Device list |
| 289 | `GET` | `/api/fleet/devices/{device_id}` | Get device details | No | - | Device dict |
| 290 | `POST` | `/api/fleet/devices/{device_id}/heartbeat` | Device heartbeat | No | `HeartbeatPayload` (cpu_percent, memory_percent, gpu_percent?, active_models, inference_count) | `{device_id, status}` |
| 291 | `GET` | `/api/fleet/health` | Fleet-wide health summary | No | - | `{total_devices, online, offline, status}` |

---

## Verticals

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 292 | `GET` | `/api/verticals/packs` | List vertical packs | No | - | Pack list (security, manufacturing, retail, healthcare, agriculture, logistics, media) |
| 293 | `GET` | `/api/verticals/packs/{pack_id}` | Get pack details | No | - | Pack dict |
| 294 | `POST` | `/api/verticals/install` | Install vertical pack | No | `InstallRequest` (pack_id) | `{pack_id, status, modules}` |
| 295 | `GET` | `/api/verticals/installed` | List installed packs | No | - | Installed pack list |
| 296 | `GET` | `/api/verticals/packs/{pack_id}/resources` | Get pack resources | No | - | `{pack_id, models, configs, pipelines, total_resources}` |

---

## Federated

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 297 | `POST` | `/api/federated/federations` | Create federation | No | `FederationCreate` (name, model_id, aggregation_strategy, min_participants, rounds, workspace_id?) | Federation dict |
| 298 | `GET` | `/api/federated/federations` | List federations | No | - | Federation list |
| 299 | `GET` | `/api/federated/federations/{federation_id}` | Get federation details | No | - | Federation dict |
| 300 | `POST` | `/api/federated/federations/{federation_id}/join` | Join federation | No | `JoinFederation` (participant_id, participant_name, data_size) | `{federation_id, participant, status}` |
| 301 | `POST` | `/api/federated/federations/{federation_id}/start-round` | Start training round | No | `StartRoundRequest` (round_number?) | `{federation_id, round, total_rounds, participants, status}` |

---

## Mobile

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 302 | `GET` | `/api/mobile/dashboard` | Mobile-optimized dashboard | No | - | `{active_streams, recent_alerts, pending_reviews, field_notes, system_status}` |
| 303 | `POST` | `/api/mobile/push/register` | Register device for push notifications | No | `PushRegister` (device_token, platform, user_id?) | Registration dict |
| 304 | `GET` | `/api/mobile/push/registrations` | List push registrations | No | - | Registration list |
| 305 | `POST` | `/api/mobile/field-notes` | Create field note from mobile | No | `FieldNoteCreate` (title, content, location?, tags, attachments) | Field note dict |
| 306 | `GET` | `/api/mobile/field-notes` | List field notes | No | - | Field note list |
| 307 | `GET` | `/api/mobile/field-notes/{note_id}` | Get field note | No | - | Field note dict |

---

## Plugins

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 308 | `POST` | `/api/plugins/register` | Register a plugin | No | `PluginRegister` (name, version, description, author, entry_point, capabilities) | Plugin dict |
| 309 | `GET` | `/api/plugins/` | List all plugins | No | - | Plugin list |
| 310 | `GET` | `/api/plugins/{plugin_id}` | Get plugin details | No | - | Plugin dict |
| 311 | `POST` | `/api/plugins/{plugin_id}/enable` | Enable plugin | No | - | `{plugin_id, enabled}` |
| 312 | `POST` | `/api/plugins/{plugin_id}/disable` | Disable plugin | No | - | `{plugin_id, enabled}` |
| 313 | `POST` | `/api/plugins/{plugin_id}/execute` | Execute plugin action | No | `PluginExecute` (action, params) | `{plugin_id, action, status, result}` |
| 314 | `GET` | `/api/plugins/marketplace/featured` | Get featured marketplace plugins | No | - | Featured plugin list |

---

## Developer

| # | Method | Path | Description | Auth | Request | Response |
|---|--------|------|-------------|------|---------|----------|
| 315 | `GET` | `/api/developer/openapi` | Get full OpenAPI spec | No | - | OpenAPI JSON |
| 316 | `GET` | `/api/developer/proto` | Get gRPC proto file info | No | - | `{filename, syntax, services, download_url}` |
| 317 | `GET` | `/api/developer/proto/download` | Download proto file content | No | - | `{content, content_type}` |
| 318 | `POST` | `/api/developer/node-templates` | Create pipeline node template | No | `NodeTemplateCreate` (name, node_type, description, default_config?) | Template dict |
| 319 | `GET` | `/api/developer/node-templates` | List node templates | No | - | Template list |
| 320 | `GET` | `/api/developer/sdks` | List available SDKs | No | - | SDK list (Python, JavaScript) |
| 321 | `GET` | `/api/developer/health` | Developer tools health check | No | - | `{api_version, openapi_available, grpc_available, sdks_available, templates_count}` |

---

## Error Responses

All endpoints return standard error responses:

| Status | Description |
|--------|-------------|
| `400` | Bad request (invalid input, missing fields) |
| `401` | Unauthorized (missing or invalid token) |
| `403` | Forbidden (insufficient permissions) |
| `404` | Resource not found |
| `422` | Validation error (invalid field values) |
| `500` | Internal server error |
| `501` | Not implemented (stub endpoint) |
| `503` | Service unavailable (dependency down) |

Error body format:
```json
{
  "detail": "Human-readable error message"
}
```

---

## Pagination

Paginated endpoints return:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

---

## Authentication Flow

1. Register: `POST /api/auth/register` with email, password, workspace_name
2. Login: `POST /api/auth/login` with email, password
3. Use the returned `access_token` as `Authorization: Bearer <token>`
4. Refresh: `POST /api/auth/refresh` with refresh_token when access token expires

---

*Total endpoints documented: 321 across 38 modules*
