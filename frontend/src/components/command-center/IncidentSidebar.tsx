"use client";

import React, { useState, useEffect, useCallback } from "react";
import type { Incident, IncidentSeverity } from "@/lib/api";
import {
  getIncidentQueue,
  assignIncident,
  escalateIncident,
  resolveIncident,
} from "@/lib/api";

const severityConfig: Record<
  IncidentSeverity,
  { border: string; bg: string; text: string; label: string }
> = {
  critical: { border: "border-l-red-600", bg: "bg-red-100", text: "text-red-800", label: "CRIT" },
  high: { border: "border-l-orange-500", bg: "bg-orange-100", text: "text-orange-800", label: "HIGH" },
  medium: { border: "border-l-yellow-500", bg: "bg-yellow-100", text: "text-yellow-800", label: "MED" },
  low: { border: "border-l-blue-500", bg: "bg-blue-100", text: "text-blue-800", label: "LOW" },
};

const severityOrder: Record<IncidentSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

interface IncidentSidebarProps {
  incidents?: Incident[];
  onRefresh?: () => void;
}

export default function IncidentSidebar({ incidents: externalIncidents, onRefresh }: IncidentSidebarProps) {
  const [incidents, setIncidents] = useState<Incident[]>(externalIncidents || []);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchIncidents = useCallback(async () => {
    try {
      const data = await getIncidentQueue();
      setIncidents(data);
    } catch {
      // keep current state on error
    }
  }, []);

  useEffect(() => {
    if (externalIncidents) {
      setIncidents(externalIncidents);
    }
  }, [externalIncidents]);

  // Auto-refresh every 10s
  useEffect(() => {
    if (externalIncidents) return; // skip polling when externally provided
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 10000);
    return () => clearInterval(interval);
  }, [fetchIncidents, externalIncidents]);

  const sorted = [...incidents].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
  );

  const handleAction = async (
    action: "assign" | "escalate" | "resolve",
    incidentId: string
  ) => {
    setLoading(true);
    try {
      if (action === "assign") await assignIncident(incidentId);
      else if (action === "escalate") await escalateIncident(incidentId);
      else await resolveIncident(incidentId);
      await fetchIncidents();
      onRefresh?.();
    } catch {
      // silent for now
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">
          Incident Queue ({sorted.length})
        </h3>
        <button
          onClick={fetchIncidents}
          className="rounded p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          title="Refresh"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {sorted.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <svg className="h-8 w-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm">No open incidents</span>
          </div>
        )}
        {sorted.map((incident) => {
          const cfg = severityConfig[incident.severity];
          const expanded = expandedId === incident.id;
          return (
            <div
              key={incident.id}
              className={`border-l-4 ${cfg.border} border-b border-gray-100 hover:bg-gray-50 transition-colors`}
            >
              <button
                onClick={() => setExpandedId(expanded ? null : incident.id)}
                className="w-full text-left px-3 py-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span
                        className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold ${cfg.bg} ${cfg.text}`}
                      >
                        {cfg.label}
                      </span>
                      <span className="text-xs text-gray-400 flex-shrink-0">
                        {timeAgo(incident.created_at)}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {incident.title}
                    </p>
                  </div>
                  {incident.assigned_operator_name && (
                    <span className="flex-shrink-0 inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-600">
                      {incident.assigned_operator_name}
                    </span>
                  )}
                </div>
              </button>

              {expanded && (
                <div className="px-3 pb-3">
                  <p className="text-xs text-gray-500 mb-3">
                    {incident.description || "No additional details."}
                  </p>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => handleAction("assign", incident.id)}
                      disabled={loading}
                      className="rounded bg-brand-600 px-2 py-1 text-[11px] font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                    >
                      Assign to Me
                    </button>
                    <button
                      onClick={() => handleAction("escalate", incident.id)}
                      disabled={loading}
                      className="rounded bg-orange-500 px-2 py-1 text-[11px] font-medium text-white hover:bg-orange-600 disabled:opacity-50"
                    >
                      Escalate
                    </button>
                    <button
                      onClick={() => handleAction("resolve", incident.id)}
                      disabled={loading}
                      className="rounded bg-green-600 px-2 py-1 text-[11px] font-medium text-white hover:bg-green-700 disabled:opacity-50"
                    >
                      Resolve
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
