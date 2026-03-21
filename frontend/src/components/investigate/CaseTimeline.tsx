"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import Button from "@/components/ui/Button";
import EventCard from "./EventCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CaseEvent {
  id: string;
  type: string;
  timestamp: string | null;
  source: string;
  payload: Record<string, unknown> | null;
  linked_asset_ids: string[];
  workspace_id: string;
  severity?: number;
  evidence_type?: string;
}

interface DateRange {
  start: string;
  end: string;
}

interface CaseTimelineProps {
  caseId: string;
  dateRange: DateRange;
  onAddEvidence: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type EventTypeKey =
  | "alert"
  | "capture_frame"
  | "audio_clip"
  | "uploaded_file"
  | "text_note"
  | "evidence"
  | "note"
  | "detection";

const EVENT_COLORS: Record<EventTypeKey, string> = {
  alert: "bg-red-500",
  detection: "bg-red-400",
  capture_frame: "bg-blue-500",
  audio_clip: "bg-blue-400",
  evidence: "bg-blue-500",
  text_note: "bg-amber-500",
  note: "bg-amber-400",
  uploaded_file: "bg-teal-500",
};

const EVENT_BORDER_COLORS: Record<EventTypeKey, string> = {
  alert: "border-red-500",
  detection: "border-red-400",
  capture_frame: "border-blue-500",
  audio_clip: "border-blue-400",
  evidence: "border-blue-500",
  text_note: "border-amber-500",
  note: "border-amber-400",
  uploaded_file: "border-teal-500",
};

function getEventColor(type: string): string {
  return EVENT_COLORS[type as EventTypeKey] || "bg-gray-400";
}

function getEventBorderColor(type: string): string {
  return EVENT_BORDER_COLORS[type as EventTypeKey] || "border-gray-400";
}

function severityToHeight(severity: number | undefined): number {
  const s = severity ?? 3;
  return 16 + (s - 1) * 6;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CaseTimeline({
  caseId,
  dateRange,
  onAddEvidence,
}: CaseTimelineProps) {
  const [events, setEvents] = useState<CaseEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<CaseEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await axios.get<CaseEvent[]>(
        `${API_BASE}/api/investigate/cases/${caseId}/events`,
        {
          params: {
            start: new Date(dateRange.start).toISOString(),
            end: new Date(dateRange.end).toISOString(),
          },
        }
      );
      setEvents(resp.data);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [caseId, dateRange.start, dateRange.end]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const rangeStart = new Date(dateRange.start).getTime();
  const rangeEnd = new Date(dateRange.end).getTime();
  const rangeMs = rangeEnd - rangeStart || 1;

  function positionPercent(timestamp: string | null): number {
    if (!timestamp) return 0;
    const t = new Date(timestamp).getTime();
    return Math.max(0, Math.min(100, ((t - rangeStart) / rangeMs) * 100));
  }

  const dateLabels: { label: string; percent: number }[] = [];
  const labelCount = Math.min(
    8,
    Math.max(2, Math.ceil(rangeMs / (1000 * 60 * 60 * 24)))
  );
  for (let i = 0; i <= labelCount; i++) {
    const t = rangeStart + (rangeMs * i) / labelCount;
    const d = new Date(t);
    dateLabels.push({
      label: d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      }),
      percent: (i / labelCount) * 100,
    });
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-700">
            Case Timeline
          </h3>
          {loading && (
            <div className="animate-spin h-4 w-4 border-2 border-brand-600 border-t-transparent rounded-full" />
          )}
        </div>
        <Button size="sm" onClick={onAddEvidence}>
          + Add Evidence
        </Button>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-red-500" />{" "}
          Alert
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-blue-500" />{" "}
          Capture
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-teal-500" />{" "}
          Analysis
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-amber-500" />{" "}
          Note
        </span>
        <span className="text-gray-400 ml-2">Height = severity</span>
      </div>

      {/* Horizontal scrollable timeline */}
      <div
        ref={scrollRef}
        className="relative w-full overflow-x-auto border border-gray-200 rounded-lg bg-white"
      >
        <div
          className="relative"
          style={{ minWidth: "800px", height: "120px" }}
        >
          {/* Axis line */}
          <div className="absolute left-4 right-4 top-[80px] h-px bg-gray-300" />

          {/* Date labels */}
          {dateLabels.map((dl, i) => (
            <div
              key={i}
              className="absolute text-[10px] text-gray-400 whitespace-nowrap"
              style={{
                left: `calc(${dl.percent}% * 0.92 + 4%)`,
                top: "90px",
              }}
            >
              {dl.label}
            </div>
          ))}

          {/* Event markers */}
          {events.map((event) => {
            const pct = positionPercent(event.timestamp);
            const h = severityToHeight(
              event.severity ??
                (event.payload as Record<string, number> | null)?.severity
            );
            const isSelected = selectedEvent?.id === event.id;

            return (
              <button
                key={event.id}
                onClick={() =>
                  setSelectedEvent(isSelected ? null : event)
                }
                className={`absolute rounded-sm transition-all cursor-pointer hover:opacity-80 ${getEventColor(
                  event.evidence_type || event.type
                )} ${
                  isSelected
                    ? "ring-2 ring-offset-1 ring-brand-500 scale-110"
                    : ""
                }`}
                style={{
                  left: `calc(${pct}% * 0.92 + 4%)`,
                  bottom: "calc(100% - 80px)",
                  width: "8px",
                  height: `${h}px`,
                  transform: "translateX(-4px)",
                }}
                title={`${event.type} - ${
                  event.timestamp
                    ? new Date(event.timestamp).toLocaleString()
                    : "no timestamp"
                }`}
              />
            );
          })}

          {/* Empty state */}
          {!loading && events.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-400">
              No events in this date range
            </div>
          )}
        </div>
      </div>

      {/* Selected event detail card */}
      {selectedEvent && (
        <div
          className={`border-l-4 ${getEventBorderColor(
            selectedEvent.evidence_type || selectedEvent.type
          )} rounded-lg`}
        >
          <EventCard event={selectedEvent} />
        </div>
      )}
    </div>
  );
}
