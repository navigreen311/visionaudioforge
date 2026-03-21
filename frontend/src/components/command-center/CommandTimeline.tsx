"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { listAlerts } from "@/lib/api";
import type { Alert, AlertSeverity } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TimelineEntry {
  id: string;
  severity: AlertSeverity;
  message: string;
  source: string;
  type: string;
  timestamp: string;
}

interface CommandTimelineProps {
  onEventClick: (event: TimelineEntry) => void;
}

// ---------------------------------------------------------------------------
// Severity styling
// ---------------------------------------------------------------------------

const severityBorder: Record<AlertSeverity, string> = {
  critical: "border-l-red-500",
  high: "border-l-red-400",
  medium: "border-l-amber-500",
  low: "border-l-blue-500",
};

const severityDot: Record<AlertSeverity, string> = {
  critical: "bg-red-500",
  high: "bg-red-400",
  medium: "bg-amber-500",
  low: "bg-blue-500",
};

const severityLabel: Record<AlertSeverity, { bg: string; text: string; label: string }> = {
  critical: { bg: "bg-red-100", text: "text-red-800", label: "CRITICAL" },
  high: { bg: "bg-red-50", text: "text-red-700", label: "HIGH" },
  medium: { bg: "bg-amber-100", text: "text-amber-800", label: "MEDIUM" },
  low: { bg: "bg-blue-100", text: "text-blue-800", label: "LOW" },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 15_000;

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function alertToEntry(alert: Alert): TimelineEntry {
  return {
    id: alert.id,
    severity: alert.severity,
    message: alert.message,
    source: alert.source ?? alert.rule_name ?? "Unknown",
    type: alert.status,
    timestamp: alert.created_at,
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CommandTimeline({ onEventClick }: CommandTimelineProps) {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isFirstLoad = useRef(true);

  const fetchAlerts = useCallback(async () => {
    try {
      const { items } = await listAlerts({ limit: 20 });
      const mapped = items.map(alertToEntry);
      // Sort newest first
      mapped.sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      );
      setEntries(mapped);
    } catch {
      // Keep current state on error
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + polling
  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  // Auto-scroll to top (newest) on new data
  useEffect(() => {
    if (scrollRef.current && isFirstLoad.current && entries.length > 0) {
      scrollRef.current.scrollTop = 0;
      isFirstLoad.current = false;
    }
  }, [entries]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">
          Event Timeline
        </h3>
        <span className="text-[10px] text-gray-400 tabular-nums">
          {entries.length} events
        </span>
      </div>

      {/* Event list */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {/* Loading skeleton */}
        {loading && entries.length === 0 && (
          <div className="px-3 py-6 text-center">
            <span className="text-xs text-gray-400">Loading events...</span>
          </div>
        )}

        {/* Empty state */}
        {!loading && entries.length === 0 && (
          <div className="flex flex-col items-center justify-center py-10 text-gray-400">
            <span className="mb-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-green-100">
              <span className="block h-2.5 w-2.5 rounded-full bg-green-500" />
            </span>
            <span className="text-sm text-green-600 font-medium">
              No recent events &mdash; all clear &#x2713;
            </span>
          </div>
        )}

        {/* Event entries */}
        {entries.map((entry) => {
          const sev = severityLabel[entry.severity];
          return (
            <button
              key={entry.id}
              onClick={() => onEventClick(entry)}
              className={`w-full text-left border-l-4 ${severityBorder[entry.severity]} border-b border-gray-100 px-3 py-2.5 hover:bg-gray-50 transition-colors`}
            >
              <div className="flex items-start gap-2">
                {/* Severity dot */}
                <span
                  className={`mt-1 flex-shrink-0 block h-2 w-2 rounded-full ${severityDot[entry.severity]}`}
                />

                <div className="flex-1 min-w-0">
                  {/* Top row: type label + source + timestamp */}
                  <div className="flex items-center gap-2 mb-0.5">
                    <span
                      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold ${sev.bg} ${sev.text}`}
                    >
                      {sev.label}
                    </span>
                    <span className="text-[10px] text-gray-500 truncate">
                      {entry.source}
                    </span>
                    <span className="ml-auto flex-shrink-0 text-[10px] text-gray-400 font-mono tabular-nums">
                      {timeAgo(entry.timestamp)}
                    </span>
                  </div>

                  {/* Message */}
                  <p className="text-xs text-gray-800 leading-relaxed truncate">
                    {entry.message}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
