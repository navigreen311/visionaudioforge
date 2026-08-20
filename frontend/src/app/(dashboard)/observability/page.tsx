"use client";

import { API_BASE_URL } from "@/lib/api";
import { readWorkspaceId } from "@/lib/session";

import { useCallback, useEffect, useState } from "react";
import TimeRangeSelector, {
  type TimeRange,
} from "@/components/observability/TimeRangeSelector";
import LatencyChart, {
  type LatencyDataPoint,
} from "@/components/observability/LatencyChart";

const API = API_BASE_URL;

// ----------------------------------------------------------------
// Interfaces
// ----------------------------------------------------------------

interface SystemOverview {
  api_status: string;
  db_status: string;
  redis_status: string;
  uptime_s: number;
  total_requests_24h: number;
  error_rate_24h: number | null;
  avg_latency_ms: number | null;
  p99_latency_ms: number | null;
}

interface PipelineHealth {
  active_pipelines: number;
  runs_24h: number;
  success_rate: number | null;
  avg_duration_ms: number | null;
  failed_runs: { id: string; error: string }[];
}

interface SLACompliance {
  compliant: boolean;
  uptime_pct: number | null;
  avg_latency_ms: number | null;
  error_rate: number | null;
  violations: string[];
}

interface ErrorTaxonomy {
  total_errors: number;
  by_type: Record<string, number>;
  by_endpoint: Record<string, number>;
  top_errors: { error: string; count: number; last_seen: string }[];
}

interface AlertFatigue {
  total_alerts: number;
  acknowledged_pct: number | null;
  avg_response_time_s: number | null;
  noisy_rules: { rule: string; count: number; ack_rate: number | null }[];
  fatigue_score: number | null;
  recommendations: string[];
}

// ----------------------------------------------------------------
// Shared UI
// ----------------------------------------------------------------

function StatusDot({ status }: { status: string }) {
  const color =
    status === "healthy"
      ? "bg-green-500"
      : status === "unhealthy"
      ? "bg-red-500"
      : "bg-yellow-500";
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />;
}

function Card({
  title,
  children,
  className = "",
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-5 shadow-sm ${className}`}
    >
      <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wide">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------

function rangeToQueryString(range: TimeRange): string {
  if (range.preset !== "custom") return `range=${range.preset}`;
  const from = range.custom?.from ?? "";
  const to = range.custom?.to ?? "";
  return `from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;
}

// ----------------------------------------------------------------
// Page
// ----------------------------------------------------------------


/**
 * A metric the platform could not measure, rendered as such.
 *
 * The server reports `null` for a metric it has no data for - `p99_latency_ms`
 * always, because the duration histogram has no quantile buckets - which is the
 * honest answer and replaced a fabricated number. This page then called
 * `.toFixed(1)` on it, threw `Cannot read properties of null`, and took the
 * whole route into the error boundary: /observability rendered "Something went
 * wrong" and nothing else, every time, for everyone.
 *
 * An em dash is the answer to "what is the p99?" when nobody measured it. A zero
 * would be a lie and a crash is worse than both.
 */
function metric(
  value: number | null | undefined,
  format: (n: number) => string,
): string {
  return value === null || value === undefined ? "\u2014" : format(value);
}

export default function ObservabilityPage() {
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [pipeline, setPipeline] = useState<PipelineHealth | null>(null);
  const [sla, setSla] = useState<SLACompliance | null>(null);
  const [errors, setErrors] = useState<ErrorTaxonomy | null>(null);
  const [fatigue, setFatigue] = useState<AlertFatigue | null>(null);
  const [latencyHistory, setLatencyHistory] = useState<LatencyDataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  const [timeRange, setTimeRange] = useState<TimeRange>({ preset: "24h" });

  const workspaceId = readWorkspaceId();

  const loadData = useCallback(async () => {
    try {
      const qs = rangeToQueryString(timeRange);

      const [ovRes, plRes, slaRes, errRes, fatRes, latRes] =
        await Promise.allSettled([
          fetch(`${API}/api/observability/dashboard`),
          fetch(`${API}/api/observability/pipeline-health`),
          fetch(`${API}/api/observability/sla?tier=standard`),
          fetch(`${API}/api/observability/errors`),
          fetch(
            `${API}/api/observability/alert-fatigue?workspace_id=${workspaceId}`,
          ),
          fetch(`${API}/api/observability/latency-history?${qs}`),
        ]);

      if (ovRes.status === "fulfilled" && ovRes.value.ok)
        setOverview(await ovRes.value.json());
      if (plRes.status === "fulfilled" && plRes.value.ok)
        setPipeline(await plRes.value.json());
      if (slaRes.status === "fulfilled" && slaRes.value.ok)
        setSla(await slaRes.value.json());
      if (errRes.status === "fulfilled" && errRes.value.ok)
        setErrors(await errRes.value.json());
      if (fatRes.status === "fulfilled" && fatRes.value.ok)
        setFatigue(await fatRes.value.json());
      if (latRes.status === "fulfilled" && latRes.value.ok) {
        const body = await latRes.value.json();
        setLatencyHistory(body.data ?? []);
      }
    } catch {
      // silently degrade
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRangeChange = (range: TimeRange) => {
    setTimeRange(range);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-400 animate-pulse">
          Loading observability data...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">
        Observability &amp; SRE Dashboard
      </h1>

      {/* ---- Time Range Selector ---- */}
      <TimeRangeSelector
        range={timeRange}
        onRangeChange={handleRangeChange}
        onRefresh={loadData}
      />

      {/* ---- System overview ---- */}
      {overview && (
        <Card title="System Overview">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center gap-2">
              <StatusDot status={overview.api_status} />
              <span className="text-sm">
                API: {overview.api_status}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <StatusDot status={overview.db_status} />
              <span className="text-sm">
                DB: {overview.db_status}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <StatusDot status={overview.redis_status} />
              <span className="text-sm">
                Redis: {overview.redis_status}
              </span>
            </div>
            <Metric
              label="Uptime"
              value={metric(overview.uptime_s, (n) => `${(n / 3600).toFixed(1)}h`)}
            />
          </div>
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <Metric
              label="Requests (24h)"
              value={metric(overview.total_requests_24h, (n) => n.toLocaleString())}
            />
            <Metric
              label="Error Rate (24h)"
              value={metric(overview.error_rate_24h, (n) => `${(n * 100).toFixed(2)}%`)}
            />
            <Metric
              label="Avg Latency"
              value={metric(overview.avg_latency_ms, (n) => `${n.toFixed(1)}ms`)}
            />
            <Metric
              label="p99 Latency"
              value={metric(overview.p99_latency_ms, (n) => `${n.toFixed(1)}ms`)}
            />
          </div>
        </Card>
      )}

      {/* ---- Latency Chart ---- */}
      <LatencyChart data={latencyHistory} slaTargetMs={500} />

      {/* ---- Pipeline health ---- */}
      {pipeline && (
        <Card title="Pipeline Health">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Metric label="Active Pipelines" value={pipeline.active_pipelines} />
            <Metric label="Runs (24h)" value={pipeline.runs_24h} />
            <Metric
              label="Success Rate"
              value={metric(pipeline.success_rate, (n) => `${(n * 100).toFixed(1)}%`)}
            />
            <Metric
              label="Avg Duration"
              value={metric(pipeline.avg_duration_ms, (n) => `${(n / 1000).toFixed(1)}s`)}
            />
          </div>
          {/* Success rate bar */}
          <div className="mt-4">
            <div className="h-3 w-full rounded-full bg-gray-200">
              <div
                className="h-3 rounded-full bg-green-500 transition-all"
                style={{ width: `${(pipeline.success_rate ?? 0) * 100}%` }}
              />
            </div>
          </div>
          {pipeline.failed_runs.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium text-red-600 mb-1">
                Recent Failures
              </p>
              <ul className="text-xs text-gray-600 space-y-1">
                {pipeline.failed_runs.map((f, i) => (
                  <li key={i}>
                    {f.id}: {f.error}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* ---- SLA compliance ---- */}
      {sla && (
        <Card title="SLA Compliance (Standard Tier)">
          <div className="flex items-center gap-4 mb-4">
            <div
              className={`text-4xl font-bold ${
                sla.compliant ? "text-green-600" : "text-red-600"
              }`}
            >
              {sla.compliant ? "COMPLIANT" : "VIOLATION"}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Metric
              label="Uptime"
              value={metric(sla.uptime_pct, (n) => `${n.toFixed(2)}%`)}
            />
            <Metric
              label="Avg Latency"
              value={metric(sla.avg_latency_ms, (n) => `${n.toFixed(1)}ms`)}
            />
            <Metric
              label="Error Rate"
              value={metric(sla.error_rate, (n) => `${(n * 100).toFixed(2)}%`)}
            />
          </div>
          {sla.violations.length > 0 && (
            <ul className="mt-3 text-sm text-red-600 space-y-1">
              {sla.violations.map((v, i) => (
                <li key={i}>- {v}</li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {/* ---- Error taxonomy ---- */}
      {errors && (
        <Card title="Error Taxonomy (24h)">
          <Metric label="Total Errors" value={errors.total_errors} />
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-500 uppercase border-b">
                <tr>
                  <th className="py-2 pr-4">Error Type</th>
                  <th className="py-2 pr-4">Count</th>
                  <th className="py-2">Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {errors.top_errors.map((e) => (
                  <tr key={e.error} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium text-gray-800">
                      {e.error}
                    </td>
                    <td className="py-2 pr-4">{e.count}</td>
                    <td className="py-2 text-gray-500">
                      {new Date(e.last_seen).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ---- Alert fatigue ---- */}
      {fatigue && (
        <Card title="Alert Fatigue Analysis">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <Metric label="Total Alerts (30d)" value={fatigue.total_alerts} />
            <Metric
              label="Acknowledged"
              value={metric(fatigue.acknowledged_pct, (n) => `${n.toFixed(1)}%`)}
            />
            <Metric
              label="Avg Response"
              value={metric(fatigue.avg_response_time_s, (n) => `${n.toFixed(0)}s`)}
            />
            <div>
              <p
                className={`text-2xl font-bold ${
                  fatigue.fatigue_score === null
                    ? "text-gray-400"
                    : fatigue.fatigue_score > 70
                    ? "text-red-600"
                    : fatigue.fatigue_score > 40
                    ? "text-yellow-600"
                    : "text-green-600"
                }`}
              >
                {metric(fatigue.fatigue_score, (n) => n.toFixed(0))}
              </p>
              <p className="text-xs text-gray-500">Fatigue Score (0-100)</p>
            </div>
          </div>

          {fatigue.noisy_rules.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-gray-600 mb-1">
                Noisy Rules
              </p>
              <ul className="text-xs text-gray-700 space-y-1">
                {fatigue.noisy_rules.map((r) => (
                  <li key={r.rule}>
                    <span className="font-medium">{r.rule}</span> — {r.count}{" "}
                    alerts, {metric(r.ack_rate, (n) => `${(n * 100).toFixed(0)}%`)} ack rate
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <p className="text-xs font-semibold text-gray-600 mb-1">
              Recommendations
            </p>
            <ul className="text-xs text-gray-700 space-y-1">
              {fatigue.recommendations.map((r, i) => (
                <li key={i}>- {r}</li>
              ))}
            </ul>
          </div>
        </Card>
      )}
    </div>
  );
}
