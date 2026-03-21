"use client";

import React, { useState, useEffect, useCallback } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DatasetOption {
  id: string;
  name: string;
  sample_count: number;
  modality: string;
}

interface ModelOption {
  id: string;
  name: string;
  version: string;
  backbone: string | null;
  status: string;
}

interface BenchmarkResultData {
  results: Record<string, Record<string, number>>;
  ranking: string[];
  duration_ms: number;
}

interface BenchmarkFormProps {
  onResults: (results: BenchmarkResultData) => void;
}

// ---------------------------------------------------------------------------
// Metric definitions
// ---------------------------------------------------------------------------

const METRIC_ROWS = [
  [
    { key: "accuracy", label: "Accuracy" },
    { key: "precision", label: "Precision" },
    { key: "recall", label: "Recall" },
    { key: "f1", label: "F1" },
  ],
  [
    { key: "auc_roc", label: "AUC-ROC" },
    { key: "auc_pr", label: "AUC-PR" },
    { key: "mcc", label: "MCC" },
    { key: "cohens_kappa", label: "Cohen's Kappa" },
  ],
  [
    { key: "mean_iou", label: "Mean IoU" },
    { key: "map_50", label: "mAP@50" },
    { key: "bleu", label: "BLEU" },
    { key: "wer", label: "WER" },
  ],
];

const DEFAULT_METRICS = ["accuracy", "precision", "recall", "f1"];

// ---------------------------------------------------------------------------
// Modality badge colors
// ---------------------------------------------------------------------------

function modalityColor(modality: string): string {
  switch (modality.toLowerCase()) {
    case "image":
      return "bg-blue-100 text-blue-800";
    case "audio":
      return "bg-purple-100 text-purple-800";
    case "video":
      return "bg-green-100 text-green-800";
    case "text":
      return "bg-amber-100 text-amber-800";
    case "multimodal":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

// ---------------------------------------------------------------------------
// Status badge colors
// ---------------------------------------------------------------------------

function statusColor(status: string): string {
  switch (status.toLowerCase()) {
    case "active":
    case "deployed":
      return "bg-green-100 text-green-800";
    case "draft":
    case "staging":
      return "bg-yellow-100 text-yellow-800";
    case "archived":
    case "retired":
      return "bg-gray-100 text-gray-600";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BenchmarkForm({ onResults }: BenchmarkFormProps) {
  // Form state
  const [name, setName] = useState("benchmark-1");
  const [datasetId, setDatasetId] = useState("");
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(DEFAULT_METRICS);
  const [customMetric, setCustomMetric] = useState("");

  // Data sources
  const [datasets, setDatasets] = useState<DatasetOption[]>([]);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [modelsLoading, setModelsLoading] = useState(false);

  // Submission
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Model dropdown open state
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);

  // ---------------------------------------------------------------------------
  // Load datasets
  // ---------------------------------------------------------------------------

  const loadDatasets = useCallback(async () => {
    setDatasetsLoading(true);
    try {
      const workspaceId =
        (typeof window !== "undefined" && localStorage.getItem("workspace_id")) ||
        "00000000-0000-0000-0000-000000000001";
      const res = await fetch(
        `${API}/api/datasets?workspace_id=${workspaceId}&limit=100`
      );
      if (!res.ok) throw new Error("Failed to load datasets");
      const data = await res.json();
      const items = data.items ?? data ?? [];
      setDatasets(
        items.map((d: Record<string, unknown>) => ({
          id: String(d.id),
          name: String(d.name ?? "Unnamed"),
          sample_count: Number(d.sample_count ?? 0),
          modality: String(d.modality ?? "unknown"),
        }))
      );
    } catch {
      setDatasets([]);
    } finally {
      setDatasetsLoading(false);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Load models
  // ---------------------------------------------------------------------------

  const loadModels = useCallback(async () => {
    setModelsLoading(true);
    try {
      const workspaceId =
        (typeof window !== "undefined" && localStorage.getItem("workspace_id")) ||
        "00000000-0000-0000-0000-000000000001";
      const res = await fetch(
        `${API}/api/registry/models?workspace_id=${workspaceId}&limit=100`
      );
      if (!res.ok) throw new Error("Failed to load models");
      const data = await res.json();
      const items = data.items ?? data ?? [];
      setModels(
        items.map((m: Record<string, unknown>) => ({
          id: String(m.id),
          name: String(m.name ?? "Unnamed"),
          version: String(m.version ?? "1.0"),
          backbone: m.backbone ? String(m.backbone) : null,
          status: String(m.status ?? "draft"),
        }))
      );
    } catch {
      setModels([]);
    } finally {
      setModelsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDatasets();
    loadModels();
  }, [loadDatasets, loadModels]);

  // ---------------------------------------------------------------------------
  // Metric toggle
  // ---------------------------------------------------------------------------

  function toggleMetric(key: string) {
    setSelectedMetrics((prev) =>
      prev.includes(key) ? prev.filter((m) => m !== key) : [...prev, key]
    );
  }

  function addCustomMetric() {
    const trimmed = customMetric.trim().toLowerCase().replace(/\s+/g, "_");
    if (trimmed && !selectedMetrics.includes(trimmed)) {
      setSelectedMetrics((prev) => [...prev, trimmed]);
      setCustomMetric("");
    }
  }

  // ---------------------------------------------------------------------------
  // Model toggle
  // ---------------------------------------------------------------------------

  function toggleModel(id: string) {
    setSelectedModelIds((prev) => {
      if (prev.includes(id)) return prev.filter((m) => m !== id);
      if (prev.length >= 10) return prev; // cap at 10
      return [...prev, id];
    });
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  async function handleSubmit() {
    setError(null);

    if (!name.trim()) {
      setError("Benchmark name is required.");
      return;
    }
    if (!datasetId) {
      setError("Please select a dataset.");
      return;
    }
    if (selectedModelIds.length < 2) {
      setError("Select at least 2 models to compare.");
      return;
    }
    if (selectedMetrics.length === 0) {
      setError("Select at least one metric.");
      return;
    }

    const workspaceId =
      (typeof window !== "undefined" && localStorage.getItem("workspace_id")) ||
      "00000000-0000-0000-0000-000000000001";

    setSubmitting(true);
    setProgress(10);

    try {
      // Step 1: Create benchmark
      const createRes = await fetch(`${API}/api/evaluation/benchmarks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          dataset_id: datasetId,
          model_ids: selectedModelIds,
          metrics: selectedMetrics,
          workspace_id: workspaceId,
        }),
      });

      if (!createRes.ok) {
        const body = await createRes.json().catch(() => ({}));
        throw new Error(
          (body as Record<string, string>).detail ?? "Failed to create benchmark"
        );
      }

      const benchmark = await createRes.json();
      setProgress(40);

      // Step 2: Run benchmark
      const runRes = await fetch(
        `${API}/api/evaluation/benchmarks/${benchmark.id}/run`,
        { method: "POST" }
      );

      if (!runRes.ok) {
        const body = await runRes.json().catch(() => ({}));
        throw new Error(
          (body as Record<string, string>).detail ?? "Failed to run benchmark"
        );
      }

      setProgress(80);
      const results: BenchmarkResultData = await runRes.json();
      setProgress(100);

      onResults(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred.");
    } finally {
      setTimeout(() => {
        setSubmitting(false);
        setProgress(0);
      }, 500);
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const allMetricKeys = METRIC_ROWS.flat().map((m) => m.key);
  const customMetrics = selectedMetrics.filter(
    (m) => !allMetricKeys.includes(m)
  );

  return (
    <Card title="Run Benchmark">
      <div className="space-y-6">
        {/* ---- Name ---- */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Benchmark Name
          </label>
          <input
            type="text"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-[#185FA5] focus:ring-1 focus:ring-[#185FA5] outline-none"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. nightly-v2-benchmark"
          />
        </div>

        {/* ---- Dataset ---- */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Dataset
          </label>
          {datasetsLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
              <LoadingDots /> Loading datasets...
            </div>
          ) : datasets.length === 0 ? (
            <p className="text-sm text-gray-400 py-2">
              No datasets yet.{" "}
              <button
                type="button"
                onClick={loadDatasets}
                className="text-[#185FA5] underline hover:text-[#134a84]"
              >
                Retry
              </button>
            </p>
          ) : (
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-[#185FA5] focus:ring-1 focus:ring-[#185FA5] outline-none bg-white"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
            >
              <option value="">-- Select a dataset --</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.sample_count.toLocaleString()} samples) [{d.modality}]
                </option>
              ))}
            </select>
          )}
          {/* Rich preview of selected dataset */}
          {datasetId && datasets.length > 0 && (
            <SelectedDatasetBadge
              dataset={datasets.find((d) => d.id === datasetId)}
            />
          )}
        </div>

        {/* ---- Models (multi-select) ---- */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Models{" "}
            <span className="text-gray-400 font-normal">
              ({selectedModelIds.length}/10 selected, min 2)
            </span>
          </label>
          {modelsLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-400 py-2">
              <LoadingDots /> Loading models...
            </div>
          ) : models.length === 0 ? (
            <p className="text-sm text-gray-400 py-2">
              No models registered yet.{" "}
              <button
                type="button"
                onClick={loadModels}
                className="text-[#185FA5] underline hover:text-[#134a84]"
              >
                Retry
              </button>
            </p>
          ) : (
            <div className="relative">
              <button
                type="button"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-left bg-white focus:border-[#185FA5] focus:ring-1 focus:ring-[#185FA5] outline-none flex items-center justify-between"
                onClick={() => setModelDropdownOpen((v) => !v)}
              >
                <span className={selectedModelIds.length === 0 ? "text-gray-400" : "text-gray-900"}>
                  {selectedModelIds.length === 0
                    ? "Select models to compare (min 2)"
                    : `${selectedModelIds.length} model${selectedModelIds.length > 1 ? "s" : ""} selected`}
                </span>
                <ChevronDown open={modelDropdownOpen} />
              </button>

              {modelDropdownOpen && (
                <div className="absolute z-20 mt-1 w-full max-h-60 overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg">
                  {models.map((m) => {
                    const checked = selectedModelIds.includes(m.id);
                    const disabled = !checked && selectedModelIds.length >= 10;
                    return (
                      <label
                        key={m.id}
                        className={`flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-gray-50 ${
                          disabled ? "opacity-50 cursor-not-allowed" : ""
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={disabled}
                          onChange={() => toggleModel(m.id)}
                          className="rounded border-gray-300 text-[#185FA5] focus:ring-[#185FA5]"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium text-gray-900 truncate">
                              {m.name}
                            </span>
                            <span className="text-xs text-gray-500">v{m.version}</span>
                            {m.backbone && (
                              <span className="text-xs bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">
                                {m.backbone}
                              </span>
                            )}
                            <span
                              className={`text-xs rounded-full px-2 py-0.5 font-medium ${statusColor(
                                m.status
                              )}`}
                            >
                              {m.status}
                            </span>
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Selected model chips */}
          {selectedModelIds.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {selectedModelIds.map((id) => {
                const m = models.find((mod) => mod.id === id);
                return (
                  <span
                    key={id}
                    className="inline-flex items-center gap-1 rounded-full bg-[#185FA5]/10 text-[#185FA5] px-2.5 py-1 text-xs font-medium"
                  >
                    {m?.name ?? id}
                    <button
                      type="button"
                      onClick={() => toggleModel(id)}
                      className="ml-0.5 hover:text-red-600"
                      aria-label={`Remove ${m?.name ?? id}`}
                    >
                      x
                    </button>
                  </span>
                );
              })}
            </div>
          )}
        </div>

        {/* ---- Metrics (checkbox grid) ---- */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Metrics
          </label>
          <div className="space-y-2">
            {METRIC_ROWS.map((row, rowIdx) => (
              <div
                key={rowIdx}
                className="grid grid-cols-2 sm:grid-cols-4 gap-2"
              >
                {row.map((metric) => (
                  <label
                    key={metric.key}
                    className={`flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer text-sm transition-colors ${
                      selectedMetrics.includes(metric.key)
                        ? "border-[#185FA5] bg-[#185FA5]/5 text-[#185FA5]"
                        : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedMetrics.includes(metric.key)}
                      onChange={() => toggleMetric(metric.key)}
                      className="rounded border-gray-300 text-[#185FA5] focus:ring-[#185FA5]"
                    />
                    {metric.label}
                  </label>
                ))}
              </div>
            ))}
          </div>

          {/* Custom metrics */}
          {customMetrics.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {customMetrics.map((m) => (
                <span
                  key={m}
                  className="inline-flex items-center gap-1 rounded-full bg-gray-100 text-gray-700 px-2.5 py-1 text-xs font-medium"
                >
                  {m}
                  <button
                    type="button"
                    onClick={() => toggleMetric(m)}
                    className="ml-0.5 hover:text-red-600"
                    aria-label={`Remove ${m}`}
                  >
                    x
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Add custom metric */}
          <div className="flex gap-2 mt-2">
            <input
              type="text"
              className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-[#185FA5] focus:ring-1 focus:ring-[#185FA5] outline-none"
              value={customMetric}
              onChange={(e) => setCustomMetric(e.target.value)}
              placeholder="Custom metric name..."
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCustomMetric();
                }
              }}
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={addCustomMetric}
              disabled={!customMetric.trim()}
            >
              Add
            </Button>
          </div>
        </div>

        {/* ---- Error ---- */}
        {error && (
          <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* ---- Progress ---- */}
        {submitting && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-500">
              <span>Running benchmark...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#185FA5] rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* ---- Submit ---- */}
        <Button
          onClick={handleSubmit}
          loading={submitting}
          disabled={submitting}
          className="w-full sm:w-auto"
        >
          Run Benchmark
        </Button>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SelectedDatasetBadge({
  dataset,
}: {
  dataset: DatasetOption | undefined;
}) {
  if (!dataset) return null;
  return (
    <div className="mt-2 inline-flex items-center gap-2 rounded-md bg-gray-50 border border-gray-200 px-3 py-1.5 text-sm">
      <span className="font-medium text-gray-900">{dataset.name}</span>
      <span className="text-gray-500">
        {dataset.sample_count.toLocaleString()} samples
      </span>
      <span
        className={`text-xs rounded-full px-2 py-0.5 font-medium ${modalityColor(
          dataset.modality
        )}`}
      >
        {dataset.modality}
      </span>
    </div>
  );
}

function ChevronDown({ open }: { open: boolean }) {
  return (
    <svg
      className={`h-4 w-4 text-gray-400 transition-transform ${
        open ? "rotate-180" : ""
      }`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}

function LoadingDots() {
  return (
    <span className="inline-flex gap-0.5">
      <span className="animate-bounce w-1.5 h-1.5 bg-gray-400 rounded-full" style={{ animationDelay: "0ms" }} />
      <span className="animate-bounce w-1.5 h-1.5 bg-gray-400 rounded-full" style={{ animationDelay: "150ms" }} />
      <span className="animate-bounce w-1.5 h-1.5 bg-gray-400 rounded-full" style={{ animationDelay: "300ms" }} />
    </span>
  );
}
