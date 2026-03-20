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
// Vision API
// ---------------------------------------------------------------------------

export interface VisionAnalyzeResult {
  processed_image?: string;
  stats?: {
    shape: number[];
    dtype: string;
    mean: number[];
    std: number[];
  };
  processing_time_ms: number;
  status?: string;
}

export interface OpticalFlowResult {
  visualization?: string;
  stats?: {
    mean_magnitude: number;
    max_magnitude: number;
    motion_area_pct: number;
  };
  processing_time_ms: number;
  status?: string;
}

export interface Detection {
  class_name: string;
  class_id: number;
  confidence: number;
  bbox: [number, number, number, number];
}

export interface DetectResult {
  detections: Detection[];
  count: number;
  visualization: string;
  processing_time_ms: number;
}

export interface OCRBlock {
  text: string;
  bbox: [number, number, number, number];
  confidence: number;
}

export interface OCRResult {
  full_text: string;
  blocks: OCRBlock[];
  processing_time_ms: number;
}

export interface ErrorAnalysisResult {
  confusion_matrix: number[][];
  classes: string[];
  per_class_metrics: {
    class_name: string;
    precision: number;
    recall: number;
    f1: number;
    support: number;
  }[];
  top_confusions: {
    true_label: string;
    predicted_label: string;
    count: number;
  }[];
  overall_accuracy: number;
}

export async function analyzeImage(
  file: File,
  operations: Record<string, unknown>,
): Promise<VisionAnalyzeResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("operations", JSON.stringify(operations));
  const { data } = await api.post("/api/vision/analyze", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function computeOpticalFlow(
  frame1: File,
  frame2: File,
  method: "lucas_kanade" | "farneback",
): Promise<OpticalFlowResult> {
  const form = new FormData();
  form.append("frame1", frame1);
  form.append("frame2", frame2);
  form.append("method", method);
  const { data } = await api.post("/api/vision/optical-flow", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function detectObjects(
  file: File,
  confidence: number,
  classes?: string,
): Promise<DetectResult> {
  const form = new FormData();
  form.append("file", file);
  const params: Record<string, string | number> = { confidence };
  if (classes) params.classes = classes;
  const { data } = await api.post("/api/vision/detect", form, {
    headers: { "Content-Type": "multipart/form-data" },
    params,
  });
  return data;
}

export async function extractText(file: File): Promise<OCRResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/api/vision/ocr", form, {
    headers: { "Content-Type": "multipart/form-data" },
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
