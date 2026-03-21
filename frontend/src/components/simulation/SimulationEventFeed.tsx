"use client";

import React, { useEffect, useRef } from "react";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SimulationEvent {
  /** 1-based sequential number. */
  seq: number;
  /** Event type label (e.g. "person_detected", "audio_anomaly"). */
  type: string;
  /** Offset from simulation start in seconds. */
  timestampOffset: number;
  /** Pipeline that produced this event. */
  pipeline: string;
  /** Confidence score 0-1. */
  confidence: number;
  /** Whether this event triggered an alert. */
  alertTriggered: boolean;
  /** Optional severity when alert is triggered. */
  severity?: "low" | "medium" | "high" | "critical";
}

interface SimulationEventFeedProps {
  events: SimulationEvent[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatOffset(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toFixed(1);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function severityVariant(severity: string | undefined): string {
  switch (severity) {
    case "critical":
      return "danger";
    case "high":
      return "error";
    case "medium":
      return "warning";
    case "low":
      return "info";
    default:
      return "neutral";
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SimulationEventFeed({ events }: SimulationEventFeedProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as new events arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events.length]);

  if (events.length === 0) {
    return (
      <Card title="Event Feed">
        <p className="text-sm text-gray-500 text-center py-8">
          No events yet. Run a simulation to see live events appear here.
        </p>
      </Card>
    );
  }

  return (
    <Card title={`Event Feed (${events.length} events)`}>
      <div
        ref={containerRef}
        className="max-h-96 overflow-y-auto space-y-2 pr-1"
      >
        {events.map((ev) => (
          <div
            key={ev.seq}
            className={`flex items-start gap-3 rounded-lg border px-4 py-3 transition-all animate-[fadeInUp_0.3s_ease-out] ${
              ev.alertTriggered
                ? "border-red-200 bg-red-50"
                : "border-gray-100 bg-gray-50"
            }`}
          >
            {/* Event # badge */}
            <span className="flex-shrink-0 flex h-7 w-7 items-center justify-center rounded-full bg-gray-200 text-xs font-bold text-gray-700">
              {ev.seq}
            </span>

            {/* Main info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold text-gray-900">{ev.type}</span>
                <span className="text-xs text-gray-400 font-mono">+{formatOffset(ev.timestampOffset)}</span>
              </div>

              <div className="mt-1 flex items-center gap-2 flex-wrap">
                {/* Thumbnail placeholder */}
                <div className="flex-shrink-0 h-8 w-12 rounded bg-gray-300 flex items-center justify-center">
                  <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
                  </svg>
                </div>

                {/* Pipeline */}
                <Badge variant="info">{ev.pipeline}</Badge>

                {/* Confidence */}
                <span className="text-xs text-gray-500">
                  conf: {(ev.confidence * 100).toFixed(0)}%
                </span>

                {/* Alert badge */}
                {ev.alertTriggered && (
                  <Badge variant={severityVariant(ev.severity)}>
                    Alert {ev.severity ? `(${ev.severity})` : ""}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <style jsx>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </Card>
  );
}
