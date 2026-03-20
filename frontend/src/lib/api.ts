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
// Alerts API
// ---------------------------------------------------------------------------

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

const WORKSPACE_ID_PARAM = "00000000-0000-0000-0000-000000000001";

function getWorkspaceId(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("workspace_id") || WORKSPACE_ID_PARAM;
  }
  return WORKSPACE_ID_PARAM;
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
