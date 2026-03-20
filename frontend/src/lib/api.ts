import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export default api;

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
  formData.append("type", type);
  if (tags.length > 0) formData.append("tags", tags.join(","));
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
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return `${base}/api/assets/${assetId}/download`;
}

// ---------------------------------------------------------------------------
// Audio Analysis API
// ---------------------------------------------------------------------------

export interface WaveformStats {
  duration: number;
  sample_rate: number;
  rms: number;
  peak: number;
  samples: number;
  image?: string;
}

export interface SpectralResult {
  image?: string;
  coefficients?: number[];
}

export interface AudioAnalysisResult {
  waveform?: WaveformStats;
  stft?: SpectralResult;
  mel?: SpectralResult;
  mfcc?: SpectralResult & { coefficients?: number[] };
}

export interface AugmentationStep {
  type: string;
  [key: string]: unknown;
}

export interface AugmentationConfig {
  preset?: string;
  steps?: AugmentationStep[];
}

export interface AugmentationResult {
  audio_base64: string;
  mime_type: string;
  applied: string[];
  original_duration: number;
  augmented_duration: number;
}

export async function analyzeAudio(
  file: File,
  operations: string[],
): Promise<AudioAnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("operations", JSON.stringify(operations));
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
  const configStr = config.preset || JSON.stringify(config.steps || []);
  formData.append("config", configStr);
  const { data } = await api.post("/api/audio/augment", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// ---------------------------------------------------------------------------
// Call Intelligence API
// ---------------------------------------------------------------------------

export interface DiarizationSegment {
  speaker: string;
  start_s: number;
  end_s: number;
  duration_s: number;
}

export interface SpeakerStats {
  total_time: number;
  percentage: number;
  avg_energy: number;
}

export interface DiarizationResult {
  segments: DiarizationSegment[];
  num_speakers: number;
  speaker_stats: Record<string, SpeakerStats>;
}

export interface CallAnalysisResult {
  transcript: string;
  speakers: DiarizationSegment[];
  summary: string;
  action_items: string[];
  sentiment: Record<
    string,
    {
      overall: string;
      scores: { positive: number; negative: number; neutral: number };
    }
  >;
  duration_s: number;
  talk_ratio: Record<
    string,
    { time_s: number; percentage: number; interruptions: number }
  >;
}

export interface TranscriptSegment {
  speaker: string;
  text: string;
  start_s: number;
  end_s: number;
}

export interface SummaryResult {
  summary: string;
  key_points: string[];
  decisions: string[];
  action_items: Array<{
    action: string;
    assignee: string | null;
    deadline: string | null;
    speaker: string;
  }>;
}

export interface SentimentResult {
  sentiment: Record<
    string,
    {
      overall: string;
      scores: { positive: number; negative: number; neutral: number };
    }
  >;
}

export async function diarizeAudio(
  file: File,
  numSpeakers?: number,
): Promise<DiarizationResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (numSpeakers !== undefined) {
    formData.append("num_speakers", String(numSpeakers));
  }
  const { data } = await api.post("/api/audio/diarize", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function analyzeCall(file: File): Promise<CallAnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/api/audio/call-analysis", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function summarizeMeeting(
  segments: TranscriptSegment[],
): Promise<SummaryResult> {
  const { data } = await api.post("/api/audio/summarize", {
    transcript_segments: segments,
  });
  return data;
}

export async function analyzeSentiment(
  segments: TranscriptSegment[],
): Promise<SentimentResult> {
  const { data } = await api.post("/api/audio/sentiment", {
    transcript_segments: segments,
  });
  return data;
}
