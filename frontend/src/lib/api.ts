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
// Alerts API
// ---------------------------------------------------------------------------

export type AlertSeverity = "critical" | "high" | "medium" | "low";
export type AlertStatus = "new" | "acknowledged" | "resolved" | "dismissed";

export interface Alert {
  id: string;
  severity: AlertSeverity;
  status: AlertStatus;
  message: string;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface AlertFilters {
  severity?: AlertSeverity;
  status?: AlertStatus;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
}

export interface AlertStats {
  total: number;
  critical_24h: number;
  acknowledged: number;
  unresolved: number;
  by_severity: Record<AlertSeverity, number>;
  by_status: Record<AlertStatus, number>;
  recent: Alert[];
}

export interface AlertRuleCondition {
  metric: string;
  operator: ">" | "<" | "==" | "!=";
  threshold: number;
  window_seconds: number;
}

export interface AlertRuleAction {
  type: "webhook" | "email" | "slack" | "log";
  target: string;
}

export interface AlertRule {
  id: string;
  name: string;
  conditions: AlertRuleCondition[];
  actions: AlertRuleAction[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AlertRuleCreatePayload {
  name: string;
  conditions: AlertRuleCondition[];
  actions: AlertRuleAction[];
  enabled: boolean;
}

export async function listAlerts(filters?: AlertFilters): Promise<Alert[]> {
  const params: Record<string, string | number> = {};
  if (filters?.severity) params.severity = filters.severity;
  if (filters?.status) params.status = filters.status;
  if (filters?.start_date) params.start_date = filters.start_date;
  if (filters?.end_date) params.end_date = filters.end_date;
  if (filters?.skip !== undefined) params.skip = filters.skip;
  if (filters?.limit !== undefined) params.limit = filters.limit;
  const { data } = await api.get("/api/alerts", { params });
  return data;
}

export async function getAlertStats(): Promise<AlertStats> {
  const { data } = await api.get("/api/alerts/stats");
  return data;
}

export async function acknowledgeAlert(id: string): Promise<Alert> {
  const { data } = await api.post(`/api/alerts/${id}/acknowledge`);
  return data;
}

export async function resolveAlert(id: string): Promise<Alert> {
  const { data } = await api.post(`/api/alerts/${id}/resolve`);
  return data;
}

export async function dismissAlert(id: string): Promise<Alert> {
  const { data } = await api.post(`/api/alerts/${id}/dismiss`);
  return data;
}

export async function listRules(): Promise<AlertRule[]> {
  const { data } = await api.get("/api/alerts/rules");
  return data;
}

export async function createRule(payload: AlertRuleCreatePayload): Promise<AlertRule> {
  const { data } = await api.post("/api/alerts/rules", payload);
  return data;
}

export async function updateRule(id: string, payload: Partial<AlertRuleCreatePayload>): Promise<AlertRule> {
  const { data } = await api.put(`/api/alerts/rules/${id}`, payload);
  return data;
}

export async function deleteRule(id: string): Promise<void> {
  await api.delete(`/api/alerts/rules/${id}`);
}
