"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface PatrolFinding {
  message: string;
  timestamp: string;
}

interface PatrolResponse {
  findings: string[];
  alerts: number;
}

interface StreamStatus {
  active: number;
  total: number;
}

interface AlertRule {
  name: string;
  enabled: boolean;
}

interface PipelineStatus {
  name: string;
  status: string;
}

interface PatrolModePanelProps {
  isActive: boolean;
}

async function fetchJson<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export default function PatrolModePanel({ isActive }: PatrolModePanelProps) {
  const [streams, setStreams] = useState<StreamStatus>({ active: 0, total: 0 });
  const [alertRules, setAlertRules] = useState<AlertRule[]>([]);
  const [pipelines, setPipelines] = useState<PipelineStatus[]>([]);
  const [lastCheck, setLastCheck] = useState<string | null>(null);
  const [patrolLog, setPatrolLog] = useState<PatrolFinding[]>([]);
  const [checking, setChecking] = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshMonitoring = useCallback(async () => {
    const [streamData, rulesData, pipelineData] = await Promise.all([
      fetchJson<StreamStatus>("/api/streams/status", { active: 0, total: 0 }),
      fetchJson<AlertRule[]>("/api/alerts/rules", []),
      fetchJson<PipelineStatus[]>("/api/pipeline/running", []),
    ]);
    setStreams(streamData);
    setAlertRules(rulesData);
    setPipelines(pipelineData);
    setLastCheck(new Date().toLocaleTimeString());
  }, []);

  const handleCheckNow = useCallback(async () => {
    setChecking(true);
    try {
      const res = await fetch("/api/agents/patrol", { method: "POST" });
      if (res.ok) {
        const data = (await res.json()) as PatrolResponse;
        const now = new Date().toLocaleTimeString();
        const newFindings: PatrolFinding[] = data.findings.map((msg) => ({
          message: msg,
          timestamp: now,
        }));
        setPatrolLog((prev) => [...newFindings, ...prev].slice(0, 5));
        setLastCheck(now);
      }
    } catch {
      // Silently handle errors; user sees stale data
    } finally {
      setChecking(false);
    }
  }, []);

  // Auto-refresh every 30 seconds while active
  useEffect(() => {
    if (!isActive) return;

    refreshMonitoring();

    intervalRef.current = setInterval(() => {
      refreshMonitoring();
    }, 30_000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isActive, refreshMonitoring]);

  const enabledRules = alertRules.filter((r) => r.enabled);
  const runningPipelines = pipelines.filter((p) => p.status === "running");

  return (
    <div
      className="overflow-hidden transition-all duration-300 ease-in-out"
      style={{
        maxHeight: isActive ? "600px" : "0px",
        opacity: isActive ? 1 : 0,
      }}
    >
      <div className="bg-white rounded-xl border border-gray-200 p-4 mt-3">
        {/* Header with pulsing dot */}
        <div className="flex items-center gap-2 mb-4">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500" />
          </span>
          <span className="text-sm font-semibold text-gray-900">
            Patrolling...
          </span>
        </div>

        {/* Monitoring list */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">Active Streams</span>
            <span className="font-medium text-gray-800">
              {streams.active}/{streams.total}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">Enabled Alert Rules</span>
            <span className="font-medium text-gray-800">
              {enabledRules.length}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">Running Pipelines</span>
            <span className="font-medium text-gray-800">
              {runningPipelines.length}
            </span>
          </div>
        </div>

        {/* Last check timestamp */}
        {lastCheck && (
          <p className="text-[10px] text-gray-400 mb-3">
            Last check: {lastCheck}
          </p>
        )}

        {/* Patrol log */}
        {patrolLog.length > 0 && (
          <div className="mb-4">
            <h4 className="text-xs font-medium text-gray-600 mb-1">
              Recent Findings
            </h4>
            <div className="space-y-1">
              {patrolLog.map((finding, idx) => (
                <div
                  key={`${finding.timestamp}-${idx}`}
                  className="flex items-start gap-2 text-[11px] text-gray-500"
                >
                  <span className="text-gray-300 shrink-0">
                    {finding.timestamp}
                  </span>
                  <span>{finding.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Check Now button */}
        <button
          onClick={handleCheckNow}
          disabled={checking}
          className="w-full bg-brand-600 text-white text-xs font-medium py-2 rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {checking ? "Checking..." : "Check Now"}
        </button>
      </div>
    </div>
  );
}
