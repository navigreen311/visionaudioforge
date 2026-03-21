"use client";

import React, { useEffect, useState, useCallback } from "react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SimulationEvent {
  timestamp: string;
  type: string;
  message: string;
  severity: "info" | "warning" | "error" | "critical";
}

interface SimulationRunSummary {
  id: string;
  name: string;
  type: "scenario" | "stress" | "edge-case";
  score: number;
  events: number;
  duration_seconds: number;
  created_at: string;
  status: "completed" | "running" | "failed";
  event_log?: SimulationEvent[];
}

interface SummaryStats {
  totalRuns: number;
  avgScore: number;
  bestScore: number;
  runsThisWeek: number;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function typeBadgeVariant(type: SimulationRunSummary["type"]): string {
  switch (type) {
    case "scenario":
      return "info";
    case "stress":
      return "warning";
    case "edge-case":
      return "error";
  }
}

function scoreColor(score: number): string {
  if (score >= 90) return "text-green-600";
  if (score >= 70) return "text-yellow-600";
  if (score >= 50) return "text-orange-500";
  return "text-red-600";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

function computeStats(runs: SimulationRunSummary[]): SummaryStats {
  if (runs.length === 0) {
    return { totalRuns: 0, avgScore: 0, bestScore: 0, runsThisWeek: 0 };
  }
  const scores = runs.map((r) => r.score);
  const now = Date.now();
  const weekAgo = now - 7 * 24 * 60 * 60 * 1000;
  const runsThisWeek = runs.filter(
    (r) => new Date(r.created_at).getTime() >= weekAgo
  ).length;
  return {
    totalRuns: runs.length,
    avgScore: Math.round(scores.reduce((a, b) => a + b, 0) / scores.length),
    bestScore: Math.max(...scores),
    runsThisWeek,
  };
}

function severityVariant(
  severity: SimulationEvent["severity"]
): string {
  switch (severity) {
    case "info":
      return "info";
    case "warning":
      return "warning";
    case "error":
      return "error";
    case "critical":
      return "danger";
  }
}

/* ------------------------------------------------------------------ */
/*  Drill-down Panel                                                   */
/* ------------------------------------------------------------------ */

function RunDrillDown({
  run,
  onClose,
}: {
  run: SimulationRunSummary;
  onClose: () => void;
}) {
  return (
    <Card className="mt-4">
      <div className="flex items-center justify-between">
        <h4 className="text-base font-semibold text-gray-900">
          {run.name} &mdash; Event Timeline
        </h4>
        <button
          onClick={onClose}
          className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 transition-colors"
        >
          Close
        </button>
      </div>

      <div className="mt-3 grid grid-cols-4 gap-3 text-center">
        <div className="rounded-md bg-gray-50 p-2">
          <p className="text-xs text-gray-500">Type</p>
          <Badge variant={typeBadgeVariant(run.type)}>{run.type}</Badge>
        </div>
        <div className="rounded-md bg-gray-50 p-2">
          <p className="text-xs text-gray-500">Score</p>
          <p className={`text-sm font-bold ${scoreColor(run.score)}`}>
            {run.score}
          </p>
        </div>
        <div className="rounded-md bg-gray-50 p-2">
          <p className="text-xs text-gray-500">Duration</p>
          <p className="text-sm font-medium text-gray-800">
            {formatDuration(run.duration_seconds)}
          </p>
        </div>
        <div className="rounded-md bg-gray-50 p-2">
          <p className="text-xs text-gray-500">Status</p>
          <Badge
            variant={
              run.status === "completed"
                ? "success"
                : run.status === "running"
                ? "warning"
                : "error"
            }
          >
            {run.status}
          </Badge>
        </div>
      </div>

      {run.event_log && run.event_log.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {run.event_log.map((evt, idx) => (
            <li
              key={idx}
              className="flex items-start gap-2 rounded border border-gray-100 p-2 text-sm"
            >
              <Badge variant={severityVariant(evt.severity)}>
                {evt.severity}
              </Badge>
              <div className="min-w-0 flex-1">
                <p className="text-gray-800">{evt.message}</p>
                <p className="text-xs text-gray-400">
                  {evt.type} &middot; {evt.timestamp}
                </p>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-center text-sm text-gray-400">
          No event log available for this run.
        </p>
      )}
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Stat Card                                                          */
/* ------------------------------------------------------------------ */

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-center shadow-sm">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-bold text-gray-900">{value}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function SimulationReportsTab() {
  const [runs, setRuns] = useState<SimulationRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<SimulationRunSummary | null>(
    null
  );
  const [exportingId, setExportingId] = useState<string | null>(null);

  /* Fetch runs */
  const fetchRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/simulation/runs");
      if (!res.ok) throw new Error(`Failed to fetch runs (${res.status})`);
      const data: SimulationRunSummary[] = await res.json();
      setRuns(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  /* Actions */
  const handleRerun = useCallback(
    async (id: string) => {
      const run = runs.find((r) => r.id === id);
      if (!run) return;
      try {
        const res = await fetch("/api/simulation/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scenario_id: id,
            config: { rerun: true, original_name: run.name },
          }),
        });
        if (!res.ok) throw new Error("Re-run failed");
        await fetchRuns();
      } catch {
        /* silent — could add toast */
      }
    },
    [runs, fetchRuns]
  );

  const handleDelete = useCallback(
    (id: string) => {
      setRuns((prev) => prev.filter((r) => r.id !== id));
      if (selectedRun?.id === id) setSelectedRun(null);
    },
    [selectedRun]
  );

  const handleExportJson = useCallback((run: SimulationRunSummary) => {
    const blob = new Blob([JSON.stringify(run, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `simulation-${run.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const handleExportPdf = useCallback(async (id: string) => {
    setExportingId(id);
    try {
      const res = await fetch(`/api/simulation/runs/${id}/report`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("PDF export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `simulation-report-${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* silent */
    } finally {
      setExportingId(null);
    }
  }, []);

  const stats = computeStats(runs);

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total Runs" value={stats.totalRuns} />
        <StatCard label="Avg Score" value={stats.avgScore} />
        <StatCard label="Best Score" value={stats.bestScore} />
        <StatCard label="Runs This Week" value={stats.runsThisWeek} />
      </div>

      {/* Run History Table */}
      <Card>
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-900">
            Run History
          </h3>
          <button
            onClick={fetchRuns}
            className="rounded border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Refresh
          </button>
        </div>

        <div className="mt-4">
          {loading && (
            <p className="py-8 text-center text-sm text-gray-400">
              Loading runs...
            </p>
          )}

          {error && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              {error}
              <button
                onClick={fetchRuns}
                className="ml-2 underline hover:no-underline"
              >
                Retry
              </button>
            </div>
          )}

          {!loading && !error && runs.length === 0 && (
            <div className="flex flex-col items-center py-10 text-gray-400">
              <svg
                className="mb-2 h-10 w-10"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="text-sm">No simulation runs yet</p>
              <p className="text-xs">
                Run a scenario to see results here.
              </p>
            </div>
          )}

          {!loading && !error && runs.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-gray-200 text-xs text-gray-500">
                  <tr>
                    <th className="pb-2 pr-4 font-medium">Run Name</th>
                    <th className="pb-2 pr-4 font-medium">Type</th>
                    <th className="pb-2 pr-4 font-medium">Score</th>
                    <th className="pb-2 pr-4 font-medium">Events</th>
                    <th className="pb-2 pr-4 font-medium">Duration</th>
                    <th className="pb-2 pr-4 font-medium">Date</th>
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {runs.map((run) => (
                    <tr
                      key={run.id}
                      onClick={() =>
                        setSelectedRun(
                          selectedRun?.id === run.id ? null : run
                        )
                      }
                      className={`cursor-pointer transition-colors hover:bg-gray-50 ${
                        selectedRun?.id === run.id ? "bg-blue-50" : ""
                      }`}
                    >
                      <td className="py-2.5 pr-4 font-medium text-gray-900">
                        {run.name}
                      </td>
                      <td className="py-2.5 pr-4">
                        <Badge variant={typeBadgeVariant(run.type)}>
                          {run.type}
                        </Badge>
                      </td>
                      <td
                        className={`py-2.5 pr-4 font-bold ${scoreColor(
                          run.score
                        )}`}
                      >
                        {run.score}
                      </td>
                      <td className="py-2.5 pr-4 text-gray-600">
                        {run.events}
                      </td>
                      <td className="py-2.5 pr-4 text-gray-600">
                        {formatDuration(run.duration_seconds)}
                      </td>
                      <td className="py-2.5 pr-4 text-gray-500">
                        {formatDate(run.created_at)}
                      </td>
                      <td className="py-2.5">
                        <div
                          className="flex gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            onClick={() => setSelectedRun(run)}
                            className="rounded border border-gray-300 px-2 py-0.5 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                          >
                            View
                          </button>
                          <button
                            onClick={() => handleRerun(run.id)}
                            className="rounded border border-blue-300 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
                          >
                            Re-run
                          </button>
                          <button
                            onClick={() => handleDelete(run.id)}
                            className="rounded border border-red-300 bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 hover:bg-red-100 transition-colors"
                          >
                            Delete
                          </button>
                          <button
                            onClick={() => handleExportJson(run)}
                            className="rounded border border-gray-300 px-2 py-0.5 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                            title="Export JSON"
                          >
                            JSON
                          </button>
                          <button
                            onClick={() => handleExportPdf(run.id)}
                            disabled={exportingId === run.id}
                            className="rounded border border-gray-300 px-2 py-0.5 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
                            title="Export PDF"
                          >
                            {exportingId === run.id ? "..." : "PDF"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      {/* Drill-down */}
      {selectedRun && (
        <RunDrillDown
          run={selectedRun}
          onClose={() => setSelectedRun(null)}
        />
      )}
    </div>
  );
}
