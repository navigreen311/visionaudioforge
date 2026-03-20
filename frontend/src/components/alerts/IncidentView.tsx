"use client";

import React, { useState } from "react";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";

interface Incident {
  incident_id: string;
  rule_id: string;
  alert_count: number;
  severity: string;
  first_alert_at: string | null;
  last_alert_at: string | null;
  alert_ids: string[];
  status: string;
}

interface TimelineEntry {
  type: string;
  timestamp: string | null;
  data: Record<string, unknown>;
}

const severityVariant: Record<string, "error" | "warning" | "info" | "neutral"> = {
  critical: "error",
  high: "warning",
  medium: "warning",
  low: "info",
};

const statusVariant: Record<string, "error" | "warning" | "success" | "neutral"> = {
  new: "error",
  acknowledged: "warning",
  resolved: "success",
  dismissed: "neutral",
};

/** Placeholder data for demonstration — wired to API in production. */
const MOCK_INCIDENTS: Incident[] = [
  {
    incident_id: "inc-001",
    rule_id: "rule-001",
    alert_count: 3,
    severity: "high",
    first_alert_at: new Date(Date.now() - 3600000).toISOString(),
    last_alert_at: new Date().toISOString(),
    alert_ids: ["a1", "a2", "a3"],
    status: "new",
  },
  {
    incident_id: "inc-002",
    rule_id: "rule-002",
    alert_count: 1,
    severity: "medium",
    first_alert_at: new Date(Date.now() - 7200000).toISOString(),
    last_alert_at: new Date(Date.now() - 7200000).toISOString(),
    alert_ids: ["a4"],
    status: "acknowledged",
  },
];

export default function IncidentView() {
  const [incidents] = useState<Incident[]>(MOCK_INCIDENTS);
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [bundleCreating, setBundleCreating] = useState(false);
  const [clipTriggering, setClipTriggering] = useState<string | null>(null);

  const handleViewTimeline = (incidentId: string) => {
    setSelectedIncident(incidentId);
    // In production: fetch from GET /api/alerts/incidents/{id}/timeline
    const incident = incidents.find((i) => i.incident_id === incidentId);
    if (incident) {
      setTimeline(
        incident.alert_ids.map((aid, idx) => ({
          type: "alert",
          timestamp: new Date(Date.now() - (incident.alert_ids.length - idx) * 600000).toISOString(),
          data: { alert_id: aid, severity: incident.severity },
        }))
      );
    }
  };

  const handleCreateBundle = async (incidentId: string) => {
    setBundleCreating(true);
    // In production: POST /api/alerts/{id}/bundle
    await new Promise((r) => setTimeout(r, 500));
    setBundleCreating(false);
    alert(`Evidence bundle created for incident ${incidentId}`);
  };

  const handleAutoClip = async (alertId: string) => {
    setClipTriggering(alertId);
    // In production: POST /api/alerts/{id}/auto-clip
    await new Promise((r) => setTimeout(r, 500));
    setClipTriggering(null);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Incidents</h2>
        <p className="text-sm text-gray-500">
          Alerts grouped by rule and time window
        </p>
      </div>

      {/* Incident cards */}
      <div className="space-y-3">
        {incidents.map((incident) => (
          <div
            key={incident.incident_id}
            className="rounded-lg border border-gray-200 bg-white shadow-sm p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant={severityVariant[incident.severity] || "neutral"}>
                    {incident.severity}
                  </Badge>
                  <Badge variant={statusVariant[incident.status] || "neutral"}>
                    {incident.status}
                  </Badge>
                  <span className="text-xs text-gray-500">
                    {incident.alert_count} alert{incident.alert_count !== 1 ? "s" : ""}
                  </span>
                </div>
                <p className="text-sm text-gray-700">
                  Rule: {incident.rule_id}
                </p>
                <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
                  {incident.first_alert_at && (
                    <span>First: {new Date(incident.first_alert_at).toLocaleString()}</span>
                  )}
                  {incident.last_alert_at && (
                    <span>Last: {new Date(incident.last_alert_at).toLocaleString()}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleViewTimeline(incident.incident_id)}
                  title="View Timeline"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={bundleCreating}
                  onClick={() => handleCreateBundle(incident.incident_id)}
                  title="Create Evidence Bundle"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </Button>
              </div>
            </div>

            {/* Timeline view (expanded) */}
            {selectedIncident === incident.incident_id && timeline.length > 0 && (
              <div className="mt-4 border-t border-gray-100 pt-4">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Timeline</h3>
                <div className="relative pl-6">
                  <div className="absolute left-2 top-0 bottom-0 w-px bg-gray-200" />
                  {timeline.map((entry, idx) => (
                    <div key={idx} className="relative mb-3 last:mb-0">
                      <div className="absolute -left-4 top-1 h-2.5 w-2.5 rounded-full bg-blue-500 ring-2 ring-white" />
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">
                          {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : "N/A"}
                        </span>
                        <Badge variant={entry.type === "alert" ? "warning" : "info"}>
                          {entry.type}
                        </Badge>
                        {entry.type === "alert" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={clipTriggering === String(entry.data.alert_id)}
                            onClick={() => handleAutoClip(String(entry.data.alert_id))}
                            title="Auto-clip"
                          >
                            {clipTriggering === String(entry.data.alert_id) ? (
                              <span className="text-xs text-gray-400">Clipping...</span>
                            ) : (
                              <svg className="h-3.5 w-3.5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={bundleCreating}
                    onClick={() => handleCreateBundle(incident.incident_id)}
                  >
                    Create Bundle
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => alert("Export feature coming soon")}
                  >
                    Export Bundle
                  </Button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {incidents.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p>No incidents found. Alerts will be grouped here when they occur.</p>
        </div>
      )}
    </div>
  );
}
