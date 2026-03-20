// ─── Auth ────────────────────────────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
}

// ─── Health ──────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version?: string;
  dependencies?: Record<string, string>;
}

// ─── Vision ──────────────────────────────────────────────────────────────────

export interface VisionAnalysisResult {
  labels: string[];
  confidence: number[];
  metadata?: Record<string, unknown>;
}

export interface DetectionResult {
  objects: Array<{
    label: string;
    confidence: number;
    bbox: [number, number, number, number];
  }>;
}

export interface OpticalFlowResult {
  flow_vectors: number[][];
  magnitude: number;
  metadata?: Record<string, unknown>;
}

export interface OCRResult {
  text: string;
  blocks: Array<{
    text: string;
    confidence: number;
    bbox: [number, number, number, number];
  }>;
}

export interface FrameDiffResult {
  diff_score: number;
  changed_regions: Array<{
    bbox: [number, number, number, number];
    magnitude: number;
  }>;
}

export interface ScreenAnalyzeResult {
  elements: Array<{
    type: string;
    text?: string;
    bbox: [number, number, number, number];
  }>;
  metadata?: Record<string, unknown>;
}

export interface ErrorAnalysisResult {
  confusion_matrix: number[][];
  class_metrics: Record<string, { precision: number; recall: number; f1: number }>;
}

// ─── Audio ───────────────────────────────────────────────────────────────────

export interface AudioAnalysisResult {
  duration: number;
  sample_rate: number;
  channels: number;
  spectral_features?: Record<string, unknown>;
}

export interface AudioAugmentResult {
  output_path: string;
  augmentations_applied: string[];
}

export interface TranscriptionResult {
  text: string;
  segments: Array<{
    start: number;
    end: number;
    text: string;
    confidence: number;
  }>;
}

export interface DiarizationResult {
  speakers: Array<{
    speaker_id: string;
    segments: Array<{ start: number; end: number }>;
  }>;
}

export interface AudioClassificationResult {
  label: string;
  confidence: number;
  all_scores: Record<string, number>;
}

// ─── Models ──────────────────────────────────────────────────────────────────

export interface ModelRegistration {
  name: string;
  version: string;
  framework: string;
  metrics?: Record<string, number>;
  metadata?: Record<string, unknown>;
}

export interface ModelInfo {
  id: string;
  name: string;
  version: string;
  framework: string;
  status: string;
  metrics?: Record<string, number>;
  created_at: string;
}

export interface ModelComparison {
  models: ModelInfo[];
  comparison: Record<string, unknown>;
}

export interface TrainingJob {
  job_id: string;
  status: string;
  model_id: string;
}

// ─── Search ──────────────────────────────────────────────────────────────────

export interface SearchQuery {
  query: string;
  modality?: 'text' | 'image' | 'audio';
  top_k?: number;
}

export interface SearchResult {
  results: Array<{
    id: string;
    score: number;
    metadata: Record<string, unknown>;
  }>;
}

export interface SearchIndexRequest {
  items: Array<{
    id: string;
    content: string;
    metadata?: Record<string, unknown>;
  }>;
}

export interface SearchStats {
  total_vectors: number;
  index_size_mb: number;
  dimensions: number;
}

// ─── Pipeline ────────────────────────────────────────────────────────────────

export interface PipelineDefinition {
  name: string;
  description?: string;
  nodes: Array<{
    id: string;
    type: string;
    config: Record<string, unknown>;
    depends_on?: string[];
  }>;
}

export interface PipelineInfo {
  id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
}

export interface PipelineRunInfo {
  run_id: string;
  pipeline_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  results?: Record<string, unknown>;
}

export interface PipelineNodeType {
  type: string;
  description: string;
  inputs: string[];
  outputs: string[];
}

// ─── Agents ──────────────────────────────────────────────────────────────────

export interface ChatMessage {
  message: string;
  agent_id?: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  response: string;
  agent_id: string;
  metadata?: Record<string, unknown>;
}

export interface AgentInfo {
  id: string;
  name: string;
  type: string;
  status: string;
}

export interface AgentCreateRequest {
  name: string;
  type: string;
  config?: Record<string, unknown>;
}

export interface MemoryEntry {
  id: string;
  content: string;
  importance: number;
  created_at: string;
}

// ─── Datasets ────────────────────────────────────────────────────────────────

export interface DatasetCreateRequest {
  name: string;
  description?: string;
  type: string;
  metadata?: Record<string, unknown>;
}

export interface DatasetInfo {
  id: string;
  name: string;
  description?: string;
  type: string;
  file_count: number;
  created_at: string;
}

export interface DatasetSplitRequest {
  train_ratio: number;
  val_ratio: number;
  test_ratio: number;
  seed?: number;
}

export interface DatasetSplitResult {
  train_count: number;
  val_count: number;
  test_count: number;
}

export interface DatasetStats {
  total_files: number;
  total_size_mb: number;
  file_types: Record<string, number>;
}

// ─── Alerts ──────────────────────────────────────────────────────────────────

export interface AlertRule {
  name: string;
  metric: string;
  condition: string;
  threshold: number;
  action?: string;
}

export interface AlertInfo {
  id: string;
  rule_name: string;
  status: string;
  triggered_at: string;
  message: string;
}

// ─── Assets ──────────────────────────────────────────────────────────────────

export interface AssetInfo {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  url: string;
  created_at: string;
}

export interface AssetUploadResult {
  id: string;
  url: string;
  filename: string;
}

// ─── Transforms ──────────────────────────────────────────────────────────────

export interface AudioTransformRequest {
  operation: string;
  params?: Record<string, unknown>;
}

export interface AudioTransformResult {
  output_path: string;
  operation: string;
  duration?: number;
}

export interface VideoTransformRequest {
  operation: string;
  params?: Record<string, unknown>;
}

export interface VideoTransformResult {
  output_path: string;
  operation: string;
  metadata?: Record<string, unknown>;
}

// ─── Common ──────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface RequestOptions {
  signal?: AbortSignal;
  headers?: Record<string, string>;
}
