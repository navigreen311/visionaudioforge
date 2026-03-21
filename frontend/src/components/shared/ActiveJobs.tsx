"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import type { Experiment } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import { SkeletonLoader } from "@/components/ui/LoadingSpinner";

// ---------------------------------------------------------------------------
// Brand Colors (inline styles where Tailwind arbitrary values aren't ideal)
// ---------------------------------------------------------------------------

const COLORS = {
  primary: "#185FA5",
  success: "#0F6E56",
  alert: "#A32D2D",
} as const;

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
  if (diffMs < 0) return "0s";
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

/**
 * Safely fetch from an endpoint that may return 404.
 * On 404 or network error, returns an empty array instead of throwing.
 */
async function safeFetchItems<T>(
  url: string,
  params: Record<string, string>,
): Promise<T[]> {
  try {
    const res = await api.get<{ items: T[] }>(url, { params });
    return res.data.items ?? [];
  } catch (err: unknown) {
    // Treat 404 as "no data" — the endpoint may not exist yet
    if (
      err !== null &&
      typeof err === "object" &&
      "response" in err &&
      (err as { response?: { status?: number } }).response?.status === 404
    ) {
      return [];
    }
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Cancel (X) icon button */
function CancelIcon({
  onClick,
  disabled,
  loading,
}: {
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
}) {
  return (
    <button
      type="button"
      title="Cancel experiment"
      aria-label="Cancel experiment"
      disabled={disabled}
      onClick={onClick}
      className="inline-flex items-center justify-center rounded p-1 transition-colors hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed"
      style={{ color: COLORS.alert }}
    >
      {loading ? (
        <svg
          className="h-4 w-4 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      ) : (
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      )}
    </button>
  );
}

/** Chevron icon that rotates when open */
function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`h-4 w-4 text-gray-500 transition-transform duration-200 ${
        open ? "rotate-180" : ""
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
  );
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

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  const fetchJobs = useCallback(async () => {
    try {
      const [exps, runs] = await Promise.all([
        safeFetchItems<ExperimentWithProgress>("/api/experiments", {
          status: "running",
        }),
        safeFetchItems<PipelineRun>("/api/pipeline/runs", {
          status: "running",
        }),
      ]);

      setExperiments(exps);
      setPipelineRuns(runs);
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

  // -----------------------------------------------------------------------
  // Handlers
  // -----------------------------------------------------------------------

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

  // -----------------------------------------------------------------------
  // Derived state
  // -----------------------------------------------------------------------

  const totalJobs = experiments.length + pipelineRuns.length;
  const isEmpty = totalJobs === 0;

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header with toggle */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-900">Active Jobs</h3>
          {fetchState === "success" && totalJobs > 0 && (
            <span
              className="inline-flex items-center justify-center rounded-full px-2 py-0.5 text-xs font-bold text-white"
              style={{ backgroundColor: COLORS.primary }}
            >
              {totalJobs}
            </span>
          )}
        </div>
        <ChevronIcon open={isOpen} />
      </button>

      {/* Collapsible body */}
      {isOpen && (
        <div className="border-t border-gray-100 px-4 py-3 space-y-4">
          {/* Loading state */}
          {fetchState === "loading" && <SkeletonLoader lines={4} />}

          {/* Error state */}
          {fetchState === "error" && (
            <div className="flex flex-col items-center gap-2 py-4">
              <p className="text-sm" style={{ color: COLORS.alert }}>
                Failed to load active jobs.
              </p>
              <Button variant="ghost" size="sm" onClick={handleRetry}>
                Retry
              </Button>
            </div>
          )}

          {/* Empty state */}
          {fetchState === "success" && isEmpty && (
            <p className="py-4 text-center text-sm text-gray-500">
              No active jobs
            </p>
          )}

          {/* Data rows */}
          {fetchState === "success" && !isEmpty && (
            <>
              {/* ── Experiments ── */}
              {experiments.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-medium uppercase tracking-wider text-gray-400">
                    Experiments
                  </h4>
                  {experiments.map((exp) => {
                    const totalEpochs =
                      exp.total_epochs ??
                      (exp.config?.epochs as number | undefined) ??
                      0;
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
                        {/* Row 1: name + model + elapsed + cancel */}
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                          <span className="text-sm font-medium text-gray-800 truncate max-w-[60%]">
                            {exp.name}
                          </span>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="text-xs text-gray-500">
                              {formatElapsed(exp.created_at)}
                            </span>
                            <CancelIcon
                              onClick={() => handleCancel(exp.id)}
                              disabled={cancellingId === exp.id}
                              loading={cancellingId === exp.id}
                            />
                          </div>
                        </div>

                        {/* Row 2: progress bar */}
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 rounded-full bg-gray-200 overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{
                                width: `${progressPct}%`,
                                backgroundColor: COLORS.primary,
                              }}
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

              {/* ── Pipeline Runs ── */}
              {pipelineRuns.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-medium uppercase tracking-wider text-gray-400">
                    Pipeline Runs
                  </h4>
                  {pipelineRuns.map((run) => (
                    <div
                      key={run.id}
                      className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 rounded-md border border-gray-100 bg-gray-50 p-3"
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
                          className="text-xs font-medium hover:underline"
                          style={{ color: COLORS.primary }}
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
