"use client";

import React, { useEffect, useState, useCallback } from "react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface BenchmarkSummary {
  id: string;
  name: string;
  modelCount: number;
  topMetric: string;
  topScore: number;
  createdAt: string;
  status: "completed" | "running" | "failed";
}

interface BenchmarkHistoryProps {
  onView?: (id: string) => void;
  onRerun?: (id: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function statusVariant(status: BenchmarkSummary["status"]): string {
  switch (status) {
    case "completed":
      return "success";
    case "running":
      return "warning";
    case "failed":
      return "error";
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function BenchmarkHistory({
  onView,
  onRerun,
}: BenchmarkHistoryProps) {
  const [benchmarks, setBenchmarks] = useState<BenchmarkSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);

  const fetchBenchmarks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/evaluation/benchmarks");
      if (!res.ok) throw new Error(`Failed to fetch benchmarks (${res.status})`);
      const data: BenchmarkSummary[] = await res.json();
      setBenchmarks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBenchmarks();
  }, [fetchBenchmarks]);

  return (
    <Card>
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between text-left"
      >
        <h3 className="text-base font-semibold text-gray-900">
          Benchmark History
        </h3>
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div className="mt-4">
          {loading && (
            <p className="py-8 text-center text-sm text-gray-400">
              Loading benchmarks...
            </p>
          )}

          {error && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              {error}
              <button
                onClick={fetchBenchmarks}
                className="ml-2 underline hover:no-underline"
              >
                Retry
              </button>
            </div>
          )}

          {!loading && !error && benchmarks.length === 0 && (
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
              <p className="text-sm">No benchmarks yet</p>
              <p className="text-xs">
                Run your first benchmark to see results here.
              </p>
            </div>
          )}

          {!loading && !error && benchmarks.length > 0 && (
            <ul className="divide-y divide-gray-100">
              {benchmarks.map((b) => (
                <li
                  key={b.id}
                  className="flex flex-wrap items-center gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-gray-900">
                      {b.name}
                    </p>
                    <div className="mt-0.5 flex flex-wrap gap-2 text-xs text-gray-500">
                      <span>{b.modelCount} models</span>
                      <span>
                        Top: <strong className="capitalize">{b.topMetric}</strong>{" "}
                        {b.topScore.toFixed(4)}
                      </span>
                      <span>{formatDate(b.createdAt)}</span>
                    </div>
                  </div>

                  <Badge variant={statusVariant(b.status)}>{b.status}</Badge>

                  <div className="flex gap-2">
                    <button
                      onClick={() => onView?.(b.id)}
                      className="rounded border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      View
                    </button>
                    <button
                      onClick={() => onRerun?.(b.id)}
                      className="rounded border border-blue-300 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
                    >
                      Re-run
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}
