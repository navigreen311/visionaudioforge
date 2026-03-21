"use client";

import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type EventType = "created" | "accessed" | "decayed" | "edited";

interface TimelineEvent {
  id: string;
  event_type: EventType;
  content: string;
  category: string;
  importance: number;
  timestamp: string;
}

interface GroupedEvents {
  label: string;
  events: TimelineEvent[];
}

const EVENT_COLORS: Record<EventType, string> = {
  created: "#22c55e",
  accessed: "#3b82f6",
  decayed: "#f59e0b",
  edited: "#a855f7",
};

const EVENT_LABELS: Record<EventType, string> = {
  created: "Created",
  accessed: "Accessed",
  decayed: "Decayed",
  edited: "Edited",
};

const EVENT_DOT_CLASSES: Record<EventType, string> = {
  created: "bg-green-500",
  accessed: "bg-blue-500",
  decayed: "bg-amber-500",
  edited: "bg-purple-500",
};

const EVENT_BADGE_CLASSES: Record<EventType, string> = {
  created: "bg-green-100 text-green-700",
  accessed: "bg-blue-100 text-blue-700",
  decayed: "bg-amber-100 text-amber-700",
  edited: "bg-purple-100 text-purple-700",
};

const ALL_EVENT_TYPES: EventType[] = ["created", "accessed", "decayed", "edited"];

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatDateLabel(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  if (target.getTime() === today.getTime()) return "Today";
  if (target.getTime() === yesterday.getTime()) return "Yesterday";
  return target.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

function getDateKey(timestamp: string): string {
  const d = new Date(timestamp);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function relativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function groupByDate(events: TimelineEvent[]): GroupedEvents[] {
  const map = new Map<string, TimelineEvent[]>();
  for (const ev of events) {
    const key = getDateKey(ev.timestamp);
    const existing = map.get(key);
    if (existing) {
      existing.push(ev);
    } else {
      map.set(key, [ev]);
    }
  }

  const groups: GroupedEvents[] = [];
  for (const [, evts] of map) {
    evts.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    groups.push({ label: formatDateLabel(evts[0].timestamp), events: evts });
  }

  // Sort groups newest first
  groups.sort((a, b) => {
    const aTs = new Date(a.events[0].timestamp).getTime();
    const bTs = new Date(b.events[0].timestamp).getTime();
    return bTs - aTs;
  });

  return groups;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function MemoryTimelineTab() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(false);

  // Filters
  const [enabledTypes, setEnabledTypes] = useState<Set<EventType>>(new Set(ALL_EVENT_TYPES));
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const loadTimeline = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (dateFrom) params.start = dateFrom;
      if (dateTo) params.end = dateTo;
      const res = await api.get("/api/memory/timeline", { params });
      setEvents(res.data);
    } catch {
      setEvents([]);
    }
    setLoading(false);
  }, [dateFrom, dateTo]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  const toggleType = (t: EventType) => {
    setEnabledTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) {
        next.delete(t);
      } else {
        next.add(t);
      }
      return next;
    });
  };

  const filtered = events.filter((ev) => enabledTypes.has(ev.event_type));
  const groups = groupByDate(filtered);

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-end">
        {/* Event type checkboxes */}
        <div className="flex gap-3">
          {ALL_EVENT_TYPES.map((t) => (
            <label key={t} className="flex items-center gap-1.5 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={enabledTypes.has(t)}
                onChange={() => toggleType(t)}
                className="rounded"
              />
              <span
                className="inline-block w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: EVENT_COLORS[t] }}
              />
              <span className="text-gray-700">{EVENT_LABELS[t]}</span>
            </label>
          ))}
        </div>

        {/* Date range */}
        <div className="flex gap-2 items-end">
          <div>
            <label className="text-xs text-gray-500">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="border rounded p-1.5 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="border rounded p-1.5 text-sm"
            />
          </div>
          <button
            onClick={loadTimeline}
            className="px-3 py-1.5 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700"
          >
            Apply
          </button>
        </div>
      </div>

      {/* Timeline list */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading timeline...</div>
      ) : groups.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No timeline events found.</div>
      ) : (
        <div className="max-h-[600px] overflow-y-auto pr-2">
          {groups.map((group) => (
            <div key={group.label} className="mb-6">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                {group.label}
              </h4>
              <div className="relative pl-6 border-l-2 border-gray-200 space-y-3">
                {group.events.map((ev) => (
                  <div key={ev.id} className="relative">
                    {/* Dot on spine */}
                    <div
                      className={`absolute -left-[29px] top-2 w-3 h-3 rounded-full border-2 border-white ${EVENT_DOT_CLASSES[ev.event_type]}`}
                    />
                    <div className="border rounded-lg p-3 hover:border-gray-300 transition-colors">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        {/* Event type badge */}
                        <span
                          className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${EVENT_BADGE_CLASSES[ev.event_type]}`}
                        >
                          {EVENT_LABELS[ev.event_type]}
                        </span>
                        {/* Category badge */}
                        <span className="text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                          {ev.category}
                        </span>
                        {/* Importance */}
                        <span className="text-[10px] text-gray-400">
                          imp: {ev.importance.toFixed(2)}
                        </span>
                        {/* Relative timestamp */}
                        <span className="text-[10px] text-gray-400 ml-auto">
                          {relativeTime(ev.timestamp)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-800">
                        {ev.content.length > 60 ? ev.content.slice(0, 60) + "..." : ev.content}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
