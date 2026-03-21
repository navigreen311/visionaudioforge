"use client";

import React from "react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ModelMetrics {
  [metric: string]: number;
}

interface ModelResult {
  name: string;
  version: string;
  status: "completed" | "running" | "failed";
  metrics: ModelMetrics;
}

export interface BenchmarkResult {
  id: string;
  name: string;
  dataset: string;
  models: ModelResult[];
  metrics: string[];
  bestModel: string;
  runtimeMs: number;
  createdAt: string;
}

interface BenchmarkResultsProps {
  results: BenchmarkResult;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function statusVariant(status: ModelResult["status"]): string {
  switch (status) {
    case "completed":
      return "success";
    case "running":
      return "warning";
    case "failed":
      return "error";
  }
}

function formatRuntime(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Determine the best and worst values for each metric across all models.
 * Higher is better for all standard metrics.
 */
function computeExtremes(models: ModelResult[], metrics: string[]) {
  const best: Record<string, number> = {};
  const worst: Record<string, number> = {};

  for (const metric of metrics) {
    let min = Infinity;
    let max = -Infinity;
    for (const model of models) {
      const v = model.metrics[metric];
      if (v === undefined) continue;
      if (v > max) max = v;
      if (v < min) min = v;
    }
    best[metric] = max;
    worst[metric] = min;
  }

  return { best, worst };
}

function cellClass(value: number, best: number, worst: number): string {
  if (best === worst) return "";
  if (value === best) return "font-bold bg-green-50 text-green-900";
  if (value === worst) return "bg-red-50 text-red-700";
  return "";
}

function downloadCsv(results: BenchmarkResult) {
  const header = ["Model", "Version", "Status", ...results.metrics];
  const rows = results.models.map((m) => [
    m.name,
    m.version,
    m.status,
    ...results.metrics.map((metric) => String(m.metrics[metric] ?? "")),
  ]);

  const csv = [header, ...rows].map((r) => r.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${results.name.replace(/\s+/g, "_")}_results.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function BenchmarkResults({ results }: BenchmarkResultsProps) {
  const { best, worst } = computeExtremes(results.models, results.metrics);

  return (
    <Card className="overflow-hidden">
      {/* Summary header */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-xl" role="img" aria-label="crown">
            &#x1F451;
          </span>
          <span className="text-lg font-semibold text-gray-900">
            {results.bestModel}
          </span>
          <Badge variant="success">Best Model</Badge>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-4 text-sm text-gray-500">
          <span>
            <strong>{results.models.length}</strong> models
          </span>
          <span>
            Dataset: <strong>{results.dataset}</strong>
          </span>
          <span>
            Runtime: <strong>{formatRuntime(results.runtimeMs)}</strong>
          </span>
        </div>
      </div>

      {/* Scorecard table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="py-2 pr-4 text-left font-medium text-gray-600">
                Model
              </th>
              {results.metrics.map((m) => (
                <th
                  key={m}
                  className="px-3 py-2 text-right font-medium text-gray-600 capitalize"
                >
                  {m}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.models.map((model) => (
              <tr
                key={model.name}
                className="border-b border-gray-100 last:border-0"
              >
                <td className="py-2 pr-4">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">
                      {model.name}
                    </span>
                    <span className="text-xs text-gray-400">
                      v{model.version}
                    </span>
                    <Badge variant={statusVariant(model.status)}>
                      {model.status}
                    </Badge>
                  </div>
                </td>
                {results.metrics.map((metric) => {
                  const value = model.metrics[metric];
                  return (
                    <td
                      key={metric}
                      className={`px-3 py-2 text-right tabular-nums ${
                        value !== undefined
                          ? cellClass(value, best[metric], worst[metric])
                          : ""
                      }`}
                    >
                      {value !== undefined ? value.toFixed(4) : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Download button */}
      <div className="mt-4 flex justify-end">
        <button
          onClick={() => downloadCsv(results)}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          Download CSV
        </button>
      </div>
    </Card>
  );
}
