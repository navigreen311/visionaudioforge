import axios from "axios";

import {
  clearSession,
  isTokenExpired,
  readAccessToken,
  readWorkspaceId,
} from "@/lib/session";

/**
 * Where the API lives.
 *
 * `docker-compose.yml` builds the frontend image with an intentionally *empty*
 * NEXT_PUBLIC_API_URL, documented there as meaning "same origin, which is what
 * nginx serves". An `||` fallback breaks that contract, because an empty string
 * is falsy: the containerised console silently fell back to
 * `http://localhost:8000`, went cross-origin, and every request died on CORS.
 * The compose smoke test could not see it — curling /api/health never exercises
 * a browser XHR. Found by the browser e2e suite.
 *
 * So: `??`, not `||`. Unset means "a dev server on 8000"; empty means
 * "same origin"; anything else is taken literally.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = readAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Every backend route now answers 401 without a valid token, so a 401 means
// this session is over — expired, revoked, or signed out in another tab.
// Clear it and hand the browser back to the login page rather than letting the
// console sit there retrying with a dead credential.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    // Only bounce to /login when the session is genuinely gone or expired.
    // Treating *any* 401 as "you are logged out" meant one misbehaving endpoint
    // could throw a working session away mid-task - which is what happened in
    // the e2e run: a single 401 on one page logged the browser out before the
    // next test. A 401 with a live token is an authorization problem for the
    // caller to surface, not a reason to end the session.
    const sessionGone = isTokenExpired(readAccessToken());
    if (status === 401 && sessionGone && typeof window !== "undefined") {
      clearSession();
      const { pathname, search } = window.location;
      if (pathname !== "/login" && pathname !== "/register") {
        const next = encodeURIComponent(`${pathname}${search}`);
        window.location.replace(`/login?next=${next}`);
      }
    }
    return Promise.reject(error);
  },
);

export default api;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * The workspace the current session acts in.
 *
 * There used to be a `00000000-0000-0000-0000-000000000001` constant here that
 * every call fell back to, which meant every browser on earth asked the API for
 * the same tenant — there was no isolation to enforce. The value now comes from
 * the authenticated session only (the token's `workspace_id` claim, or the
 * `user.workspace_id` returned by `/api/auth/me`), and there is no default.
 *
 * Throws when there is no session. Callers are inside the console, which is
 * gated by `src/middleware.ts` and the dashboard layout, so reaching this
 * without a session is a bug worth surfacing rather than papering over with
 * somebody else's tenant id.
 */
function getWorkspaceId(): string {
  const workspaceId = readWorkspaceId();
  if (!workspaceId) {
    throw new Error(
      "No workspace in the current session. Sign in again — the workspace is " +
        "read from the authenticated session and is never defaulted.",
    );
  }
  return workspaceId;
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export interface UserResponse {
  id: string;
  email: string;
  workspace_id: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: UserResponse;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post("/api/auth/login", { email, password });
  return data;
}

export async function register(
  email: string,
  password: string,
  workspace_name: string,
): Promise<AuthResponse> {
  const { data } = await api.post("/api/auth/register", { email, password, workspace_name });
  return data;
}

export async function refresh(refreshToken: string): Promise<TokenResponse> {
  const { data } = await api.post("/api/auth/refresh", { refresh_token: refreshToken });
  return data;
}

export async function getMe(): Promise<UserResponse> {
  const { data } = await api.get("/api/auth/me");
  return data;
}

// ---------------------------------------------------------------------------
// Vision API
// ---------------------------------------------------------------------------

export interface VisionImageStats {
  shape: number[];
  dtype: string;
  mean: number[];
  std: number[];
}

export interface VisionAnalyzeResult {
  /** Base64 PNG of the processed image. The endpoint names this `image`;
   *  `processed_image` never appears in a response and is kept only so older
   *  callers keep compiling. */
  image?: string;
  processed_image?: string;
  stats?: VisionImageStats;
  processing_time_ms?: number;
  histogram?: { r: number[]; g: number[]; b: number[] };
  stft?: unknown;
  mel?: unknown;
  mfcc?: unknown;
  waveform?: unknown;
  [key: string]: unknown;
}

export interface OpticalFlowStats {
  mean_magnitude: number;
  max_magnitude: number;
  motion_area_pct: number;
}

export interface OpticalFlowResult {
  flow_magnitude: number;
  flow_image?: string;
  visualization?: string;
  stats?: OpticalFlowStats;
  processing_time_ms?: number;
  [key: string]: unknown;
}

export interface Detection {
  label?: string;
  class_name?: string;
  class_id?: number;
  confidence: number;
  bbox: number[];
}

export interface DetectResult {
  detections: Detection[];
  count: number;
  visualization?: string;
  image_b64?: string;
  processing_time_ms?: number;
  [key: string]: unknown;
}

export interface OCRBlock {
  text: string;
  confidence: number;
  bbox: number[];
}

export interface OCRResult {
  full_text?: string;
  text: string;
  blocks: OCRBlock[];
  words: Array<{ text: string; confidence: number; bbox: number[] }>;
  language?: string;
  confidence?: number;
  processing_time_ms?: number;
  [key: string]: unknown;
}

export interface PerClassMetric {
  class_name: string;
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface TopConfusion {
  true_label: string;
  predicted_label: string;
  count: number;
}

export interface ErrorAnalysisResult {
  overall_accuracy: number;
  classes: string[];
  confusion_matrix: number[][];
  per_class_metrics: PerClassMetric[];
  top_confusions: TopConfusion[];
  summary: string;
  errors: Array<{ type: string; description: string; severity: string }>;
  [key: string]: unknown;
}

export async function analyzeImage(
  file: File,
  // An array of {op, params} steps, which is what the endpoint validates for.
  // It was typed as a Record, which let the caller send an object the server
  // rejects and made the mismatch invisible to the type checker.
  operations?: Array<{ op: string; params: Record<string, unknown> }>,
): Promise<VisionAnalyzeResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (operations) formData.append("operations", JSON.stringify(operations));
  const { data } = await api.post("/api/vision/analyze", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function computeOpticalFlow(
  frame1: File,
  frame2: File,
  method?: string,
): Promise<OpticalFlowResult> {
  const formData = new FormData();
  formData.append("frame1", frame1);
  formData.append("frame2", frame2);
  if (method) formData.append("method", method);
  const { data } = await api.post("/api/vision/optical-flow", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function detectObjects(
  file: File,
  confidence?: number,
  classFilter?: string,
  iouThreshold?: number,
  maxDetections?: number,
): Promise<DetectResult> {
  const formData = new FormData();
  formData.append("file", file);
  const params: Record<string, string | number> = {};
  if (confidence !== undefined) params.confidence = confidence;
  if (iouThreshold !== undefined) params.iou_threshold = iouThreshold;
  if (maxDetections !== undefined) params.max_detections = maxDetections;
  if (classFilter) params.classes = classFilter;
  const { data } = await api.post("/api/vision/detect", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    params,
  });
  return data;
}

export async function extractText(
  file: File,
  language?: string,
  outputFormat?: string,
  confidenceFilter?: number,
): Promise<OCRResult> {
  const formData = new FormData();
  formData.append("file", file);
  const params: Record<string, string | number> = {};
  if (language) params.language = language;
  if (outputFormat) params.output_format = outputFormat;
  if (confidenceFilter !== undefined) params.confidence_filter = confidenceFilter;
  const { data } = await api.post("/api/vision/ocr", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    params,
  });
  return data;
}

export async function analyzeErrors(
  predictions: string[],
  groundTruth: string[],
  classes: string[],
): Promise<ErrorAnalysisResult> {
  const { data } = await api.post("/api/vision/error-analysis", {
    predictions,
    ground_truth: groundTruth,
    classes,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Audio API
// ---------------------------------------------------------------------------

export interface SpectrogramData {
  image?: string;
  [key: string]: unknown;
}

export interface MfccData extends SpectrogramData {
  coefficients?: number[][];
}

export interface WaveformData {
  image?: string;
  duration: number;
  sample_rate: number;
  rms: number;
  peak: number;
  samples: number;
  [key: string]: unknown;
}

export interface AudioAnalysisResult {
  stft?: SpectrogramData;
  mel?: SpectrogramData;
  mfcc?: MfccData;
  waveform?: WaveformData;
  [key: string]: unknown;
}

/**
 * A single augmentation step, mirroring the backend `AugmentationStep` schema
 * (backend/app/schemas/audio.py).
 *
 * `type` names an augmentation. The accepted set is the `_ALIASES` table in
 * backend/app/services/audio/augmentation.py: "noise", "white_noise",
 * "pink_noise", "brown_noise", "stretch", "time_stretch", "pitch",
 * "pitch_shift", "shift", "time_shift", "freq_mask", "frequency_mask" and
 * "time_mask". `params` is normalised to the underlying method's keywords, so
 * both `semitones` and `n_steps` work, as do `shift_pct` and `shift_ms`.
 *
 * An unknown name is a 400 listing the ones that work - it used to be a 500
 * with an empty body, which is how two panels shipped speaking a vocabulary
 * this server did not accept.
 */
export interface AugmentationStep {
  type: string;
  /** Probability of applying this step, 0-1. Server defaults to 1.0. */
  probability?: number;
  params: Record<string, string | number>;
}

export interface AugmentationConfig {
  preset?: string;
  steps?: AugmentationStep[];
}

export interface AugmentationResult {
  audio_base64: string;
  mime_type: string;
  sample_rate: number;
  duration: number;
  original_duration: number;
  augmented_duration: number;
  applied: string[];
  steps_applied: string[];
}

export interface SpeakerSentiment {
  overall: string;
  scores: {
    positive: number;
    negative: number;
    neutral: number;
  };
}

export interface TalkRatioEntry {
  percentage: number;
  time_s: number;
  interruptions: number;
}

export interface SpeakerSegment {
  speaker: string;
  start_s: number;
  end_s: number;
}

export interface CallAnalysisResult {
  transcript: string;
  sentiment: Record<string, SpeakerSentiment>;
  topics: string[];
  summary: string;
  duration_s: number;
  speakers: SpeakerSegment[];
  action_items: string[];
  talk_ratio: Record<string, TalkRatioEntry>;
  [key: string]: unknown;
}

export async function analyzeAudio(
  file: File,
  operations: string[],
): Promise<AudioAnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);
  operations.forEach((op) => formData.append("operations", op));
  const { data } = await api.post("/api/audio/analyze", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function augmentAudio(
  file: File,
  config: AugmentationConfig,
): Promise<AugmentationResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("config", JSON.stringify(config));
  const { data } = await api.post("/api/audio/augment", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function transcribeAudio(
  file: File,
  language?: string,
): Promise<{ text: string; segments: unknown[] }> {
  const formData = new FormData();
  formData.append("file", file);
  if (language) formData.append("language", language);
  const { data } = await api.post("/api/audio/transcribe", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function diarizeAudio(
  file: File,
): Promise<{ segments: Array<{ speaker: string; start: number; end: number; text?: string }> }> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/api/audio/diarize", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function analyzeCall(
  file: File,
): Promise<CallAnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/api/audio/analyze-call", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Model Registry API
// ---------------------------------------------------------------------------

export interface ModelRecord {
  id: string;
  name: string;
  version: string;
  status: string;
  backbone: string | null;
  metrics: Record<string, number | string> | null;
  workspace_id: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedModels {
  items: ModelRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ModelCreatePayload {
  name: string;
  version: string;
  backbone?: string;
  metrics?: Record<string, number | string>;
  workspace_id: string;
}

export interface CompareResult {
  model_a: { id: string; name: string; version: string; metrics: Record<string, number> };
  model_b: { id: string; name: string; version: string; metrics: Record<string, number> };
  metric_diffs: Record<string, { model_a: number | null; model_b: number | null; diff: number | null }>;
}

export async function listModels(
  workspaceId: string,
  status?: string,
  skip = 0,
  limit = 20,
): Promise<PaginatedModels> {
  const params: Record<string, string | number> = { workspace_id: workspaceId, skip, limit };
  if (status) params.status = status;
  const { data } = await api.get("/api/registry/models", { params });
  return data;
}

export async function registerModel(payload: ModelCreatePayload): Promise<ModelRecord> {
  const { data } = await api.post("/api/registry/register", payload);
  return data;
}

export async function getModel(modelId: string): Promise<ModelRecord> {
  const { data } = await api.get(`/api/registry/models/${modelId}`);
  return data;
}

export async function updateModelStatus(modelId: string, status: string): Promise<ModelRecord> {
  const { data } = await api.put(`/api/registry/models/${modelId}/status`, { status });
  return data;
}

export async function compareModels(modelAId: string, modelBId: string): Promise<CompareResult> {
  const { data } = await api.post("/api/registry/compare", {
    model_a_id: modelAId,
    model_b_id: modelBId,
  });
  return data;
}

export async function rollbackModel(modelId: string, toVersion: string): Promise<ModelRecord> {
  const { data } = await api.post(`/api/registry/models/${modelId}/rollback`, {
    to_version: toVersion,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Experiments API
// ---------------------------------------------------------------------------

export interface Experiment {
  id: string;
  name: string;
  model_id: string;
  dataset_id: string;
  config: Record<string, unknown>;
  status: string;
  metrics?: Record<string, number>;
  created_at: string;
  updated_at: string;
}

export interface PaginatedExperiments {
  items: Experiment[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export async function listExperiments(
  skip = 0,
  limit = 20,
): Promise<PaginatedExperiments> {
  const { data } = await api.get("/api/experiments", {
    params: { skip, limit, workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function createExperiment(payload: {
  name: string;
  model_id: string;
  dataset_id: string;
  config: Record<string, unknown>;
}): Promise<Experiment> {
  const { data } = await api.post("/api/experiments", {
    ...payload,
    workspace_id: getWorkspaceId(),
  });
  return data;
}

export async function startTraining(experimentId: string): Promise<Experiment> {
  const { data } = await api.post(`/api/experiments/${experimentId}/epochs`, {
    action: "start",
  });
  return data;
}

// ---------------------------------------------------------------------------
// Datasets API
// ---------------------------------------------------------------------------

export interface DatasetSplit {
  train: number;
  val: number;
  test: number;
}

export interface Dataset {
  id: string;
  name: string;
  modality: string;
  format: string;
  sample_count: number;
  size_bytes: number;
  version: number;
  split: DatasetSplit;
  class_counts: Record<string, number>;
  workspace_id: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedDatasets {
  items: Dataset[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export async function listDatasets(
  skip = 0,
  limit = 20,
): Promise<PaginatedDatasets> {
  const { data } = await api.get("/api/datasets", {
    params: { skip, limit, workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function createDataset(payload: {
  name: string;
  format: string;
}): Promise<Dataset> {
  const { data } = await api.post("/api/datasets", {
    ...payload,
    workspace_id: getWorkspaceId(),
  });
  return data;
}

export async function uploadSamples(
  datasetId: string,
  file: File,
): Promise<{ count: number }> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post(`/api/datasets/${datasetId}/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function splitDataset(
  datasetId: string,
  ratios: { train: number; val: number; test: number },
): Promise<{ train: number; val: number; test: number }> {
  const { data } = await api.post(`/api/datasets/${datasetId}/split`, ratios);
  return data;
}

// ---------------------------------------------------------------------------
// Search API
// ---------------------------------------------------------------------------

export interface SearchResult {
  id: string;
  asset_id: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query_time_ms: number;
}

export interface StatsResponse {
  total_indexed: number;
  by_modality: Record<string, number>;
}

export async function searchQuery(
  query: string,
  k = 10,
  modality?: string,
): Promise<SearchResponse> {
  const { data } = await api.post("/api/search/query", { query, k, modality });
  return data;
}

export async function indexAsset(body: {
  asset_id: string;
  modality: string;
  content_url: string;
}): Promise<{ status: string; asset_id: string }> {
  const { data } = await api.post("/api/search/index", body);
  return data;
}

export async function searchStats(): Promise<StatsResponse> {
  const { data } = await api.get("/api/search/stats");
  return data;
}

// ---------------------------------------------------------------------------
// Pipeline API
// ---------------------------------------------------------------------------

export interface PipelineNode {
  type: string;
  label: string;
  description: string;
  inputs: string[];
  outputs: string[];
}

export interface Pipeline {
  id: string;
  name: string;
  description?: string;
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
  workspace_id: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedPipelines {
  items: Pipeline[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PipelineRunStart {
  run_id: string;
  status: string;
}

export async function listPipelines(
  skip = 0,
  limit = 20,
): Promise<PaginatedPipelines> {
  const { data } = await api.get("/api/pipelines", {
    params: { skip, limit, workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function createPipeline(payload: {
  name: string;
  description?: string;
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
}): Promise<Pipeline> {
  const { data } = await api.post("/api/pipeline/create", {
    ...payload,
    workspace_id: getWorkspaceId(),
  });
  return data;
}

export async function runPipeline(pipelineId: string): Promise<PipelineRunStart> {
  const { data } = await api.post(`/api/pipeline/run/${pipelineId}`);
  return data;
}

export async function listNodes(): Promise<PipelineNode[]> {
  const { data } = await api.get("/api/pipeline/nodes");
  return data;
}

export async function generateFromDescription(
  description: string,
): Promise<{ nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] }> {
  const { data } = await api.post("/api/pipeline/generate", { description });
  return data;
}

export async function listSavedPipelines(
  page = 1,
  pageSize = 20,
): Promise<PaginatedPipelines> {
  const { data } = await api.get("/api/pipeline/list", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function savePipeline(payload: {
  name: string;
  description?: string;
  definition: Record<string, unknown>;
}): Promise<Pipeline> {
  const { data } = await api.post("/api/pipeline/save", {
    ...payload,
    workspace_id: getWorkspaceId(),
  });
  return data;
}

// ---------------------------------------------------------------------------
// Alerts API
// ---------------------------------------------------------------------------

export type AlertSeverity = "critical" | "high" | "medium" | "low";
/**
 * Mirrors the backend `AlertStatus` enum (backend/app/models/alert.py); the
 * alerts API serialises these values verbatim. Note the open state is "new" —
 * there is no "firing" status server-side.
 */
export type AlertStatus = "new" | "acknowledged" | "resolved" | "dismissed";

export interface AlertEvidence {
  type: "image" | "video" | "none";
  url?: string;
  thumbnail_url?: string;
}

export interface AlertHistoryEntry {
  id: string;
  status: AlertStatus;
  created_at: string;
}

export interface Alert {
  id: string;
  rule_id: string;
  rule_name?: string;
  severity: AlertSeverity;
  status: AlertStatus;
  message: string;
  metric_value: number;
  threshold: number;
  source?: string;
  workspace_id: string;
  evidence?: AlertEvidence;
  created_at: string;
  updated_at: string;
}

export interface AlertFilters {
  severity?: AlertSeverity;
  status?: AlertStatus;
  start_date?: string;
  end_date?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface AlertStatsData {
  total: number;
  by_severity: Record<AlertSeverity, number>;
  by_status: Record<AlertStatus, number>;
  critical_24h: number;
  acknowledged: number;
  unresolved: number;
  recent: Alert[];
}

export interface AlertStatsSummary {
  critical: number;
  critical_trend: number;
  warning: number;
  warning_trend: number;
  info: number;
  info_trend: number;
  acknowledged_today: number;
  acknowledged_today_trend: number;
}

export interface AlertRuleCondition {
  metric: string;
  operator: ">" | "<" | "==" | "!=" | ">=" | "<=";
  threshold: number;
  window_seconds: number;
}

export interface AlertRuleAction {
  type: "webhook" | "email" | "slack" | "discord" | "sms" | "log";
  target: string;
}

export interface AlertRule {
  id: string;
  name: string;
  conditions: AlertRuleCondition[];
  actions: AlertRuleAction[];
  enabled: boolean;
  workspace_id: string;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// AL4 — Alert Rules Tab types
// ---------------------------------------------------------------------------

export type AL4Severity = "critical" | "warning" | "info";
export type AL4ConditionField = "confidence" | "class" | "motion" | "audio_level" | "ocr_text" | "custom";
export type AL4Operator = ">" | "<" | "=" | "contains" | "not_contains";
export type AL4LogicOperator = "AND" | "OR";
export type AL4Cooldown = "none" | "1m" | "5m" | "15m" | "1h";
export type AL4DeliveryChannel = "email" | "slack" | "webhook";

export interface AL4Condition {
  id: string;
  field: AL4ConditionField;
  operator: AL4Operator;
  value: string;
}

export interface AL4Actions {
  email: { enabled: boolean; address: string };
  slack: { enabled: boolean; webhook_url: string };
  webhook: { enabled: boolean; post_url: string };
  auto_clip: boolean;
}

export interface AL4RulePayload {
  name: string;
  severity: AL4Severity;
  conditions: AL4Condition[];
  logic_operator: AL4LogicOperator;
  cooldown: AL4Cooldown;
  actions: AL4Actions;
  enabled: boolean;
}

export interface AL4Rule extends AL4RulePayload {
  id: string;
  trigger_count: number;
  trigger_window_days: number;
  created_at: string;
  updated_at: string;
}

export async function listAL4Rules(): Promise<AL4Rule[]> {
  const { data } = await api.get("/api/alerts/rules/al4", {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function createAL4Rule(payload: AL4RulePayload): Promise<AL4Rule> {
  const { data } = await api.post("/api/alerts/rules/al4", payload, {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function duplicateAL4Rule(ruleId: string): Promise<AL4Rule> {
  const { data } = await api.post(`/api/alerts/rules/al4/${ruleId}/duplicate`, null, {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function deleteAL4Rule(ruleId: string): Promise<void> {
  await api.delete(`/api/alerts/rules/al4/${ruleId}`);
}

export async function toggleAL4Rule(ruleId: string, enabled: boolean): Promise<AL4Rule> {
  const { data } = await api.patch(`/api/alerts/rules/al4/${ruleId}`, { enabled });
  return data;
}

export interface AlertRuleCreatePayload {
  name: string;
  conditions: AlertRuleCondition[] | Record<string, unknown>;
  actions: AlertRuleAction[] | Record<string, unknown>[];
  enabled: boolean;
  escalation_config?: EscalationConfig;
}

export interface EscalationLevel {
  after_minutes: number;
  action: string;
}

export interface EscalationConfig {
  levels: EscalationLevel[];
}

export interface DeliveryTestResult {
  status: string;
  note?: string;
  status_code?: number;
  response_time_ms?: number;
}

export interface RuleTestResult {
  triggered: boolean;
  matched_conditions: string[];
  details: string;
}

export async function listAlerts(filters: AlertFilters = {}): Promise<{ items: Alert[]; total: number }> {
  const { data } = await api.get("/api/alerts", {
    params: { workspace_id: getWorkspaceId(), ...filters },
  });
  return data;
}

export async function getAlertStats(): Promise<AlertStatsData> {
  const { data } = await api.get("/api/alerts/stats", {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function getAlertStatsSummary(): Promise<AlertStatsSummary> {
  const { data } = await api.get("/api/alerts/stats/summary", {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

/**
 * An alerts incident: alerts grouped by rule and time window.
 *
 * Named apart from the command-centre `Incident` below, which is a different
 * thing with the same word - a case record with a title and an assignee. They
 * are not interchangeable and merging them silently widened that one's
 * `severity` from a union to `string`.
 */
export interface AlertIncident {
  incident_id: string;
  rule_id: string;
  alert_count: number;
  severity: string;
  first_alert_at: string | null;
  last_alert_at: string | null;
  alert_ids: string[];
  status: string;
}

export interface AlertIncidentTimelineEntry {
  type: string;
  timestamp: string | null;
  data: Record<string, unknown>;
}

/**
 * Incidents are alerts grouped by rule and time window, computed server-side.
 *
 * `IncidentView` shipped with a `MOCK_INCIDENTS` array and comments reading
 * "In production: fetch from ...". The endpoints it named all existed - the
 * component was rendering three invented incidents on the alerts page's
 * Incidents tab, in production, to whoever opened it.
 */
export async function listIncidents(windowMinutes = 30): Promise<{
  incidents: AlertIncident[];
  total: number;
}> {
  const { data } = await api.get("/api/alerts/incidents", {
    params: { workspace_id: getWorkspaceId(), window_minutes: windowMinutes },
  });
  return data;
}

export async function getIncidentTimeline(
  incidentId: string,
): Promise<{ incident_id: string; timeline: AlertIncidentTimelineEntry[] }> {
  const { data } = await api.get(`/api/alerts/incidents/${incidentId}/timeline`, {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

/** Get or create the evidence bundle for an incident. */
export async function createIncidentBundle(
  incidentId: string,
): Promise<Record<string, unknown>> {
  const { data } = await api.get(`/api/alerts/incidents/${incidentId}/bundle`);
  return data;
}

/**
 * Download an evidence bundle.
 *
 * The endpoint answers with a Content-Disposition attachment, so this hands the
 * blob to the browser rather than returning it - the caller has nothing useful
 * to do with the bytes.
 */
export async function exportEvidenceBundle(bundleId: string): Promise<void> {
  const response = await api.get(`/api/alerts/bundles/${bundleId}/export`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `evidence-bundle-${bundleId}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function triggerAutoClip(alertId: string): Promise<Record<string, unknown>> {
  const { data } = await api.post(`/api/alerts/${alertId}/auto-clip`);
  return data;
}

export async function updateAlertStatus(
  alertId: string,
  status: AlertStatus,
): Promise<Alert> {
  const { data } = await api.patch(`/api/alerts/${alertId}`, { status });
  return data;
}

export async function acknowledgeAlert(alertId: string): Promise<Alert> {
  const { data } = await api.post(`/api/alerts/${alertId}/acknowledge`);
  return data;
}

export async function resolveAlert(alertId: string): Promise<Alert> {
  const { data } = await api.post(`/api/alerts/${alertId}/resolve`);
  return data;
}

export async function dismissAlert(alertId: string): Promise<Alert> {
  const { data } = await api.post(`/api/alerts/${alertId}/dismiss`);
  return data;
}

export async function patchAlertStatus(
  alertId: string,
  status: AlertStatus,
): Promise<Alert> {
  const { data } = await api.patch(`/api/alerts/${alertId}`, { status });
  return data;
}

export async function getAlertHistory(
  ruleId: string,
): Promise<AlertHistoryEntry[]> {
  const { data } = await api.get("/api/alerts/history", {
    params: { rule_id: ruleId, limit: 5 },
  });
  return data;
}

export async function listRules(): Promise<AlertRule[]> {
  const { data } = await api.get("/api/alerts/rules", {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function createRule(payload: AlertRuleCreatePayload): Promise<AlertRule> {
  const { data } = await api.post("/api/alerts/rules", payload, {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function updateRule(
  ruleId: string,
  payload: Partial<AlertRuleCreatePayload>,
): Promise<AlertRule> {
  const { data } = await api.put(`/api/alerts/rules/${ruleId}`, payload);
  return data;
}

export async function deleteRule(ruleId: string): Promise<void> {
  await api.delete(`/api/alerts/rules/${ruleId}`);
}

export async function testRule(
  ruleId: string,
  conditions: Record<string, unknown>,
  sampleMetrics: Record<string, number>,
): Promise<RuleTestResult> {
  const { data } = await api.post(`/api/alerts/rules/${ruleId}/test`, {
    conditions,
    sample_metrics: sampleMetrics,
  });
  return data;
}

export async function testDeliveryChannel(
  channel: string,
  config: Record<string, unknown>,
): Promise<DeliveryTestResult> {
  const { data } = await api.post("/api/alerts/delivery/test", { channel, config });
  return data;
}

export interface NotificationChannelConfig {
  type: "slack" | "email" | "webhook";
  enabled: boolean;
  severity_filter: ("critical" | "warning" | "info")[];
  slack?: {
    webhook_url: string;
    channel_name: string;
  };
  email?: {
    recipients: string[];
    subject_prefix: string;
  };
  webhook?: {
    url: string;
    headers: Record<string, string>;
    payload_template: string;
  };
}

export interface ChannelTestResult {
  success: boolean;
  message: string;
}

export async function testNotificationChannel(
  config: NotificationChannelConfig,
): Promise<ChannelTestResult> {
  const { data } = await api.post("/api/alerts/channels/test", config);
  return data;
}

export async function saveNotificationChannel(
  config: NotificationChannelConfig,
): Promise<NotificationChannelConfig> {
  const { data } = await api.post("/api/alerts/channels", config);
  return data;
}

export async function listEscalations(): Promise<unknown[]> {
  const { data } = await api.get("/api/alerts/escalations", {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function escalateAlert(
  alertId: string,
  escalationConfig: EscalationConfig,
): Promise<unknown> {
  const { data } = await api.post(`/api/alerts/${alertId}/escalate`, {
    escalation_config: escalationConfig,
  });
  return data;
}

// ---------------------------------------------------------------------------
// Agents API
// ---------------------------------------------------------------------------

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  actions?: Array<{ type: string; description: string }>;
}

export interface Agent {
  id: string;
  name: string;
  type: string;
  status: string;
  workspace_id: string;
  created_at: string;
}

export interface Memory {
  id: string;
  agent_id: string;
  content: string;
  importance: number;
  created_at: string;
}

export async function chatWithCopilot(
  agentId: string,
  message: string,
  history?: ChatMessage[],
): Promise<ChatResponse> {
  const { data } = await api.post("/api/agents/chat", {
    agent_id: agentId,
    message,
    history: history || [],
  });
  return data;
}

export async function listAgents(): Promise<Agent[]> {
  const { data } = await api.get("/api/agents", {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function createAgent(payload: {
  name: string;
  type: string;
}): Promise<Agent> {
  const { data } = await api.post("/api/agents", {
    ...payload,
    workspace_id: getWorkspaceId(),
  });
  return data;
}

export async function getMemory(agentId: string): Promise<Memory[]> {
  const { data } = await api.get(`/api/agents/${agentId}/memory`);
  return data;
}

// ---------------------------------------------------------------------------
// Assets API
// ---------------------------------------------------------------------------

export type AssetType = "image" | "video" | "audio";

export interface Asset {
  id: string;
  filename: string;
  type: AssetType;
  size: number;
  tags: string[];
  mime_type: string;
  width?: number;
  height?: number;
  duration?: number;
  thumbnail_url?: string;
  url?: string;
  /**
   * Search-index state for this asset. Optional: the assets API does not
   * populate it yet, so the UI must treat "absent" as "unknown" rather than
   * assuming a value.
   */
  index_status?: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedAssets {
  items: Asset[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AssetFiltersParams {
  type?: AssetType;
  tags?: string;
  search?: string;
  sort_by?: "created_at" | "filename" | "size";
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export async function listAssets(filters: AssetFiltersParams = {}): Promise<PaginatedAssets> {
  const params: Record<string, string | number> = {};
  if (filters.type) params.type = filters.type;
  if (filters.tags) params.tags = filters.tags;
  if (filters.search) params.search = filters.search;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.sort_dir) params.sort_dir = filters.sort_dir;
  if (filters.page) params.page = filters.page;
  if (filters.page_size) params.page_size = filters.page_size;
  const { data } = await api.get("/api/assets", { params });
  return data;
}

export async function uploadAsset(
  file: File,
  type: AssetType,
  tags: string[],
  onProgress?: (pct: number) => void,
): Promise<Asset> {
  const formData = new FormData();
  formData.append("file", file);
  // The field is `asset_type`, and tags are JSON. Sending `type` and a
  // comma-separated string meant every upload from the console 422'd - asset
  // upload had never once worked from the UI. Found by the browser e2e suite.
  formData.append("asset_type", type);
  if (tags.length > 0) formData.append("tags", JSON.stringify(tags));
  const { data } = await api.post("/api/assets/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });
  return data;
}

export async function getAsset(assetId: string): Promise<Asset> {
  const { data } = await api.get(`/api/assets/${assetId}`);
  return data;
}

export async function updateAsset(
  assetId: string,
  updates: { tags?: string[]; filename?: string },
): Promise<Asset> {
  const { data } = await api.put(`/api/assets/${assetId}`, updates);
  return data;
}

export async function deleteAsset(assetId: string): Promise<void> {
  await api.delete(`/api/assets/${assetId}`);
}

export function downloadAssetUrl(assetId: string): string {
  const base = API_BASE_URL;
  return `${base}/api/assets/${assetId}/download`;
}

// ---------------------------------------------------------------------------
// Transform API
// ---------------------------------------------------------------------------

export interface TransformResult {
  output_url?: string;
  output_base64?: string;
  duration?: number;
  [key: string]: unknown;
}

export async function audioTransform(
  file: File,
  operations: Array<{ name: string; params?: Record<string, unknown> }>,
): Promise<TransformResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("operations", JSON.stringify(operations));
  const { data } = await api.post("/api/transform/audio/chain", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function videoTransform(
  file: File,
  operation: string,
  params?: Record<string, unknown>,
): Promise<TransformResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("operation", operation);
  if (params) formData.append("params", JSON.stringify(params));
  const { data } = await api.post(`/api/transform/video/${operation}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Command Center API
// ---------------------------------------------------------------------------

export type StreamSourceType = "camera" | "rtsp" | "screen";
export type StreamStatus = "online" | "offline" | "degraded";
export type IncidentSeverity = "critical" | "high" | "medium" | "low";
export type IncidentStatus = "open" | "assigned" | "escalated" | "resolved";
export type GridLayout = "2x2" | "3x3" | "4x4" | "1+3" | "1+5";

export interface Stream {
  id: string;
  name: string;
  source_type: StreamSourceType;
  url?: string;
  status: StreamStatus;
  fps: number;
  position: number;
  is_primary: boolean;
  created_at: string;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  assigned_to?: string;
  assigned_operator_name?: string;
  stream_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Shift {
  id: string;
  operator_id: string;
  operator_name: string;
  zone: string;
  started_at: string;
  ended_at?: string;
  handoff_notes?: string;
}

export interface CockpitOverview {
  system_status: "green" | "yellow" | "red";
  active_streams: number;
  open_incidents: number;
  active_operators: number;
  current_layout: GridLayout;
}

export interface KPIs {
  avg_response_time_seconds: number;
  response_time_trend: number;
  resolution_rate_pct: number;
  resolution_rate_trend: number;
  false_alarm_rate_pct: number;
  false_alarm_trend: number;
  incidents_today: number;
  incidents_today_trend: number;
}

export interface TimelineEvent {
  id: string;
  type: "alert" | "incident" | "stream" | "operator" | "system";
  description: string;
  timestamp: string;
}

export interface AddStreamPayload {
  name: string;
  source_type: StreamSourceType;
  url?: string;
  position?: number;
}

export async function listStreams(): Promise<Stream[]> {
  const { data } = await api.get("/api/command-center/streams");
  return data;
}

export async function addStream(payload: AddStreamPayload): Promise<Stream> {
  const { data } = await api.post("/api/command-center/streams", payload);
  return data;
}

export async function removeStream(streamId: string): Promise<void> {
  await api.delete(`/api/command-center/streams/${streamId}`);
}

export async function getStreamHealth(streamId: string): Promise<{ status: StreamStatus; fps: number }> {
  const { data } = await api.get(`/api/command-center/streams/${streamId}/health`);
  return data;
}

export async function getLayout(): Promise<{ layout: GridLayout }> {
  const { data } = await api.get("/api/command-center/layout");
  return data;
}

export async function setLayout(layout: GridLayout): Promise<{ layout: GridLayout }> {
  const { data } = await api.put("/api/command-center/layout", { layout });
  return data;
}

export async function createShift(zone: string): Promise<Shift> {
  const { data } = await api.post("/api/command-center/shifts", { zone });
  return data;
}

export async function endShift(shiftId: string, handoffNotes?: string): Promise<Shift> {
  const { data } = await api.put(`/api/command-center/shifts/${shiftId}/end`, {
    handoff_notes: handoffNotes,
  });
  return data;
}

export async function getIncidentQueue(): Promise<Incident[]> {
  const { data } = await api.get("/api/command-center/incidents");
  return data;
}

export async function assignIncident(incidentId: string): Promise<Incident> {
  const { data } = await api.post(`/api/command-center/incidents/${incidentId}/assign`);
  return data;
}

export async function escalateIncident(incidentId: string): Promise<Incident> {
  const { data } = await api.post(`/api/command-center/incidents/${incidentId}/escalate`);
  return data;
}

export async function resolveIncident(incidentId: string): Promise<Incident> {
  const { data } = await api.post(`/api/command-center/incidents/${incidentId}/resolve`);
  return data;
}

export async function getCockpitOverview(): Promise<CockpitOverview> {
  const { data } = await api.get("/api/command-center/overview");
  return data;
}

export async function getKPIs(): Promise<KPIs> {
  const { data } = await api.get("/api/command-center/kpis");
  return data;
}

export async function getTimelineFeed(): Promise<TimelineEvent[]> {
  const { data } = await api.get("/api/command-center/timeline");
  return data;
}

// ---------------------------------------------------------------------------
// Settings — API Keys
// ---------------------------------------------------------------------------

export interface APIKeyScope {
  module: string;
  permissions: string[];
}

export interface APIKeyRead {
  id: string;
  name: string;
  key_prefix: string;
  scopes: APIKeyScope[];
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
  is_active: boolean;
}

export interface APIKeyCreatePayload {
  name: string;
  scopes: APIKeyScope[];
  expires_in_days: number | null;
}

export interface APIKeyCreated {
  id: string;
  name: string;
  key: string;
  scopes: APIKeyScope[];
  created_at: string;
  expires_at: string | null;
}

export async function listAPIKeys(): Promise<APIKeyRead[]> {
  const { data } = await api.get("/api/settings/api-keys", {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function createAPIKey(payload: APIKeyCreatePayload): Promise<APIKeyCreated> {
  const { data } = await api.post("/api/settings/api-keys", payload, {
    params: { workspace_id: getWorkspaceId() },
  });
  return data;
}

export async function revokeAPIKey(keyId: string): Promise<void> {
  await api.delete(`/api/settings/api-keys/${keyId}`, {
    params: { workspace_id: getWorkspaceId() },
  });
}


/**
 * Where the WebSocket endpoints live.
 *
 * Derived from the page's own origin rather than named, for the same reason
 * `API_BASE_URL` defaults to same-origin in the container: nginx serves the
 * console and proxies `/ws`, so the socket belongs on whatever origin the
 * browser is already on. Pages used to write `ws://localhost:8000` themselves,
 * which connects only on a developer machine with the API port published.
 *
 * `NEXT_PUBLIC_WS_URL` still overrides it, and an explicit `NEXT_PUBLIC_API_URL`
 * is honoured next, so a split deployment can still point the socket elsewhere.
 */
export function wsBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_WS_URL;
  if (configured) return configured.replace(/^http/, "ws").replace(/\/+$/, "");

  if (API_BASE_URL) {
    return API_BASE_URL.replace(/^http/, "ws").replace(/\/+$/, "");
  }

  if (typeof window !== "undefined") {
    const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${scheme}//${window.location.host}`;
  }

  return "";
}
