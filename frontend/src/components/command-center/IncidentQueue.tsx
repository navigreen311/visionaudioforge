"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import type { Alert, AlertSeverity, AlertStatus } from "@/lib/api";
import { listAlerts } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface IncidentQueueProps {
  onIncidentClick: (alert: Alert) => void;
}

// ---------------------------------------------------------------------------
// Severity display config
// ---------------------------------------------------------------------------

const severityConfig: Record<
  AlertSeverity,
  { border: string; bg: string; text: string; label: string }
> = {
  critical: {
    border: "border-l-red-600",
    bg: "bg-red-100",
    text: "text-red-800",
    label: "CRIT",
  },
  high: {
    border: "border-l-orange-500",
    bg: "bg-orange-100",
    text: "text-orange-800",
    label: "HIGH",
  },
  medium: {
    border: "border-l-yellow-500",
    bg: "bg-yellow-100",
    text: "text-yellow-800",
    label: "MED",
  },
  low: {
    border: "border-l-blue-500",
    bg: "bg-blue-100",
    text: "text-blue-800",
    label: "LOW",
  },
};

const severityOrder: Record<AlertSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const statusBadge: Record<AlertStatus, { bg: string; text: string; label: string }> = {
  firing: { bg: "bg-red-50", text: "text-red-700", label: "Open" },
  acknowledged: { bg: "bg-yellow-50", text: "text-yellow-700", label: "Acknowledged" },
  resolved: { bg: "bg-green-50", text: "text-green-700", label: "Resolved" },
  dismissed: { bg: "bg-gray-50", text: "text-gray-500", label: "Dismissed" },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function elapsedTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ${mins % 60}m`;
  return `${Math.floor(hours / 24)}d ${hours % 24}h`;
}

function truncate(str: string, max: number): string {
  if (str.length <= max) return str;
  return str.slice(0, max).trimEnd() + "\u2026";
}

// ---------------------------------------------------------------------------
// Polling interval
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 30_000;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function IncidentQueue({ onIncidentClick }: IncidentQueueProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const { items } = await listAlerts({ status: "firing" });
      setAlerts(items);
    } catch {
      // keep current state on error
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + polling every 30 s
  useEffect(() => {
    fetchAlerts();
    intervalRef.current = setInterval(fetchAlerts, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchAlerts]);

  // Sort by severity priority
  const sorted = [...alerts].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity],
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">
          Incident Queue ({sorted.length})
        </h3>
        <button
          onClick={fetchAlerts}
          disabled={loading}
          className="rounded p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 disabled:opacity-50"
          title="Refresh"
        >
          <svg
            className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>

      {/* Alert rows */}
      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <svg
              className="h-8 w-8 mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-sm">No open incidents</span>
          </div>
        )}

        {sorted.map((alert) => {
          const sev = severityConfig[alert.severity];
          const sts = statusBadge[alert.status];

          return (
            <button
              key={alert.id}
              onClick={() => onIncidentClick(alert)}
              className={`w-full text-left border-l-4 ${sev.border} border-b border-gray-100 hover:bg-gray-50 transition-colors px-3 py-2.5`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  {/* Priority badge + elapsed */}
                  <div className="flex items-center gap-2 mb-0.5">
                    <span
                      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold ${sev.bg} ${sev.text}`}
                    >
                      {sev.label}
                    </span>
                    <span className="text-xs text-gray-400 flex-shrink-0">
                      {elapsedTime(alert.created_at)}
                    </span>
                  </div>

                  {/* Description truncated */}
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {truncate(alert.message, 80)}
                  </p>

                  {/* Source + zone */}
                  <div className="flex items-center gap-2 mt-0.5">
                    {alert.source && (
                      <span className="text-[10px] text-gray-500 truncate max-w-[120px]">
                        {alert.source}
                      </span>
                    )}
                    {alert.rule_name && (
                      <span className="text-[10px] text-gray-400 truncate max-w-[100px]">
                        {alert.rule_name}
                      </span>
                    )}
                  </div>
                </div>

                {/* Status badge */}
                <span
                  className={`flex-shrink-0 inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${sts.bg} ${sts.text}`}
                >
                  {sts.label}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
