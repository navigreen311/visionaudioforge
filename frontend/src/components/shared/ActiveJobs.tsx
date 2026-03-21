"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import type { Experiment } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import { SkeletonLoader } from "@/components/ui/LoadingSpinner";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PipelineRun {
  id: string;
  name: string;
  status: string;
  started_at: string;
}

interface ExperimentWithProgress extends Experiment {
  current_epoch?: number;
  total_epochs?: number;
}

type FetchState = "loading" | "success" | "error";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatElapsed(startIso: string): string {
  const diffMs = Date.now() - new Date(startIso).getTime();
  const totalSeconds = Math.floor(diffMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function statusVariant(status: string): string {
  switch (status) {
    case "running":
      return "info";
    case "completed":
    case "success":
      return "success";
    case "failed":
    case "error":
      return "error";
    default:
      return "neutral";
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const REFRESH_INTERVAL_MS = 15_000;

export default function ActiveJobs() {
  const [isOpen, setIsOpen] = useState(true);
  const [fetchState, setFetchState] = useState<FetchState>("loading");
  const [experiments, setExperiments] = useState<ExperimentWithProgress[]>([]);
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const [expRes, pipeRes] = await Promise.all([
        api.get<{ items: ExperimentWithProgress[] }>("/api/experiments", {
          params: { status: "running" },
        }),
        api.get<{ items: PipelineRun[] }>("/api/pipeline/runs", {
          params: { status: "running" },
        }),
      ]);

      setExperiments(expRes.data.items ?? []);
      setPipelineRuns(pipeRes.data.items ?? []);
      setFetchState("success");
    } catch {
      setFetchState("error");
    }
  }, []);

  useEffect(() => {
    fetchJobs();

    intervalRef.current = setInterval(fetchJobs, REFRESH_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchJobs]);

  const handleCancel = async (experimentId: string) => {
    setCancellingId(experimentId);
    try {
      await api.post(`/api/experiments/${experimentId}/cancel`);
      await fetchJobs();
    } finally {
      setCancellingId(null);
    }
  };

  const handleRetry = () => {
    setFetchState("loading");
    fetchJobs();
  };

  const isEmpty = experiments.length === 0 && pipelineRuns.length === 0;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header with toggle */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
      >
        <h3 className="text-sm font-semibold text-gray-900">Active Jobs</h3>
        <svg
          className={`h-4 w-4 text-gray-500 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Collapsible body */}
      {isOpen && (
        <div className="border-t border-gray-100 px-4 py-3 space-y-4">
          {/* Loading state */}
          {fetchState === "loading" && (
            <SkeletonLoader lines={4} />
          )}

          {/* Error state */}
          {fetchState === "error" && (
            <div className="flex flex-col items-center gap-2 py-4">
              <p className="text-sm text-red-600">
                Failed to load active jobs.
              </p>
              <Button variant="ghost" size="sm" onClick={handleRetry}>
                Retry
              </Button>
            </div>
          )}

          {/* Success state */}
          {fetchState === "success" && isEmpty && (
            <p className="py-4 text-center text-sm text-gray-500">
              No active jobs
            </p>
          )}

          {fetchState === "success" && !isEmpty && (
            <>
              {/* Experiments */}
              {experiments.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-medium uppercase tracking-wider text-gray-400">
                    Experiments
                  </h4>
                  {experiments.map((exp) => {
                    const totalEpochs = exp.total_epochs ?? (exp.config?.epochs as number | undefined) ?? 0;
                    const currentEpoch = exp.current_epoch ?? 0;
                    const progressPct =
                      totalEpochs > 0
                        ? Math.round((currentEpoch / totalEpochs) * 100)
                        : 0;

                    return (
                      <div
                        key={exp.id}
                        className="rounded-md border border-gray-100 bg-gray-50 p-3 space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-800 truncate">
                            {exp.name}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500">
                              {formatElapsed(exp.created_at)}
                            </span>
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={cancellingId === exp.id}
                              onClick={() => handleCancel(exp.id)}
                            >
                              {cancellingId === exp.id ? "..." : "Cancel"}
                            </Button>
                          </div>
                        </div>

                        {/* Progress bar */}
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 rounded-full bg-gray-200 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-blue-600 transition-all duration-300"
                              style={{ width: `${progressPct}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-600 whitespace-nowrap">
                            {currentEpoch}/{totalEpochs} epochs
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Pipeline Runs */}
              {pipelineRuns.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-medium uppercase tracking-wider text-gray-400">
                    Pipeline Runs
                  </h4>
                  {pipelineRuns.map((run) => (
                    <div
                      key={run.id}
                      className="flex items-center justify-between rounded-md border border-gray-100 bg-gray-50 p-3"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-sm font-medium text-gray-800 truncate">
                          {run.name}
                        </span>
                        <Badge variant={statusVariant(run.status)}>
                          {run.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-xs text-gray-500">
                          {formatElapsed(run.started_at)}
                        </span>
                        <a
                          href={`/pipeline?run=${run.id}`}
                          className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
                        >
                          View
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
