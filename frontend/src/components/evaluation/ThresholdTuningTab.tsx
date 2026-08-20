"use client";

import { API_BASE_URL } from "@/lib/api";

import React, { useState, useMemo, useCallback } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import PRCurveChart from "./PRCurveChart";
import ROCCurveChart from "./ROCCurveChart";
import type { PRPoint } from "./PRCurveChart";
import type { ROCPoint } from "./ROCCurveChart";

const API = API_BASE_URL;

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ThresholdStats {
  threshold: number;
  precision: number;
  recall: number;
  f1: number;
  fpr: number;
  accuracy: number;
}

interface ThresholdAnalysisResponse {
  pr_curve: PRPoint[];
  roc_curve: ROCPoint[];
  auc_pr: number;
  auc_roc: number;
  threshold_stats: ThresholdStats[];
  optimal_f1_threshold: number;
  optimal_precision_threshold: number;
  optimal_recall_threshold: number;
}

interface BenchmarkOption {
  id: string;
  label: string;
  predictions: string;
  groundTruth: string;
}

/* ------------------------------------------------------------------ */
/*  Mock benchmark presets                                              */
/* ------------------------------------------------------------------ */

const BENCHMARK_PRESETS: BenchmarkOption[] = [
  {
    id: "balanced",
    label: "Balanced Binary (20 samples)",
    predictions:
      "0.05, 0.12, 0.18, 0.25, 0.30, 0.35, 0.42, 0.48, 0.52, 0.58, 0.62, 0.68, 0.72, 0.78, 0.82, 0.85, 0.88, 0.92, 0.95, 0.98",
    groundTruth: "0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1",
  },
  {
    id: "imbalanced",
    label: "Imbalanced (high negative ratio)",
    predictions:
      "0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.55, 0.60, 0.70, 0.80, 0.90, 0.95, 0.12, 0.18, 0.22, 0.28",
    groundTruth: "0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0",
  },
  {
    id: "wellseparated",
    label: "Well-Separated Classes",
    predictions:
      "0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.85, 0.88, 0.90, 0.92, 0.94, 0.96, 0.98, 0.03, 0.07, 0.11, 0.91, 0.95",
    groundTruth: "0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1",
  },
];

/* ------------------------------------------------------------------ */
/*  Stat Row Component                                                 */
/* ------------------------------------------------------------------ */

function StatBox({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-lg px-4 py-3 text-center ${
        highlight
          ? "bg-brand-50 border border-brand-200"
          : "bg-gray-50 border border-gray-200"
      }`}
    >
      <p className="text-xs font-medium uppercase text-gray-500">{label}</p>
      <p
        className={`text-xl font-bold ${highlight ? "text-brand-700" : "text-gray-900"}`}
      >
        {value}
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function ThresholdTuningTab() {
  const [predictionsRaw, setPredictionsRaw] = useState(
    "0.1, 0.4, 0.35, 0.8, 0.65, 0.9, 0.2, 0.55, 0.7, 0.95",
  );
  const [truthRaw, setTruthRaw] = useState("0, 0, 1, 1, 1, 1, 0, 1, 0, 1");
  const [result, setResult] = useState<ThresholdAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.5);

  /* ---- Benchmark loader ---- */
  const handleLoadBenchmark = useCallback((presetId: string) => {
    const preset = BENCHMARK_PRESETS.find((b) => b.id === presetId);
    if (preset) {
      setPredictionsRaw(preset.predictions);
      setTruthRaw(preset.groundTruth);
    }
  }, []);

  /* ---- Compute curves ---- */
  const handleCompute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const predictions = predictionsRaw
        .split(",")
        .map((x) => parseFloat(x.trim()))
        .filter((n) => !isNaN(n));
      const ground_truth = truthRaw
        .split(",")
        .map((x) => parseInt(x.trim(), 10))
        .filter((n) => !isNaN(n));

      if (predictions.length === 0 || ground_truth.length === 0) {
        setError("Please enter valid predictions and ground truth values.");
        return;
      }
      if (predictions.length !== ground_truth.length) {
        setError(
          `Length mismatch: ${predictions.length} predictions vs ${ground_truth.length} ground truth values.`,
        );
        return;
      }

      const res = await fetch(`${API}/api/evaluation/threshold-curves`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ predictions, ground_truth }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `HTTP ${res.status}`);
      }

      const data: ThresholdAnalysisResponse = await res.json();
      setResult(data);
      setThreshold(data.optimal_f1_threshold);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [predictionsRaw, truthRaw]);

  /* ---- Interpolated stats at current threshold ---- */
  const currentStats = useMemo((): ThresholdStats | null => {
    if (!result) return null;
    const stats = result.threshold_stats;
    if (stats.length === 0) return null;

    let closest = stats[0];
    let minDist = Math.abs(stats[0].threshold - threshold);
    for (const s of stats) {
      const d = Math.abs(s.threshold - threshold);
      if (d < minDist) {
        minDist = d;
        closest = s;
      }
    }
    return closest;
  }, [result, threshold]);

  /* ---- Optimal buttons ---- */
  const handleSetOptimalF1 = useCallback(() => {
    if (result) setThreshold(result.optimal_f1_threshold);
  }, [result]);

  const handleSetOptimalPrecision = useCallback(() => {
    if (result) setThreshold(result.optimal_precision_threshold);
  }, [result]);

  const handleSetOptimalRecall = useCallback(() => {
    if (result) setThreshold(result.optimal_recall_threshold);
  }, [result]);

  /* ---- Threshold comparison table ---- */
  const comparisonThresholds = useMemo(() => {
    if (!result) return [];
    const targets = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9];
    return targets.map((t) => {
      const stats = result.threshold_stats;
      let closest = stats[0];
      let minDist = Math.abs(stats[0].threshold - t);
      for (const s of stats) {
        const d = Math.abs(s.threshold - t);
        if (d < minDist) {
          minDist = d;
          closest = s;
        }
      }
      return closest;
    });
  }, [result]);

  return (
    <div className="space-y-6">
      {/* Input section */}
      <Card title="Threshold Curve Analysis">
        <div className="space-y-4">
          {/* Benchmark loader */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Load from benchmark
            </label>
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              defaultValue=""
              onChange={(e) => {
                if (e.target.value) handleLoadBenchmark(e.target.value);
              }}
            >
              <option value="" disabled>
                Select a benchmark preset...
              </option>
              {BENCHMARK_PRESETS.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.label}
                </option>
              ))}
            </select>
          </div>

          {/* Textareas */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Predictions (comma-separated floats 0-1)
            </label>
            <textarea
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              rows={2}
              value={predictionsRaw}
              onChange={(e) => setPredictionsRaw(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ground Truth (comma-separated 0 or 1)
            </label>
            <textarea
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              rows={2}
              value={truthRaw}
              onChange={(e) => setTruthRaw(e.target.value)}
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <Button onClick={handleCompute} loading={loading}>
            Compute Curves
          </Button>
        </div>
      </Card>

      {/* Results */}
      {result && (
        <>
          {/* Charts side-by-side */}
          <Card title="PR & ROC Curves">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                  Precision-Recall Curve
                </h4>
                <PRCurveChart
                  data={result.pr_curve}
                  currentThreshold={threshold}
                  onThresholdChange={setThreshold}
                  aucPR={result.auc_pr}
                />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                  ROC Curve
                </h4>
                <ROCCurveChart
                  data={result.roc_curve}
                  currentThreshold={threshold}
                  onThresholdChange={setThreshold}
                  aucROC={result.auc_roc}
                />
              </div>
            </div>
          </Card>

          {/* Threshold slider */}
          <Card title="Threshold Control">
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">
                    Decision Threshold
                  </label>
                  <span className="text-lg font-bold text-gray-900 font-mono">
                    {threshold.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0.00</span>
                  <span>0.25</span>
                  <span>0.50</span>
                  <span>0.75</span>
                  <span>1.00</span>
                </div>
              </div>

              {/* Optimal buttons */}
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" onClick={handleSetOptimalF1}>
                  Optimal F1 ({result.optimal_f1_threshold.toFixed(2)})
                </Button>
                <Button variant="secondary" size="sm" onClick={handleSetOptimalPrecision}>
                  Optimal Precision ({result.optimal_precision_threshold.toFixed(2)})
                </Button>
                <Button variant="secondary" size="sm" onClick={handleSetOptimalRecall}>
                  Optimal Recall ({result.optimal_recall_threshold.toFixed(2)})
                </Button>
              </div>

              {/* Stat row */}
              {currentStats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatBox label="Precision" value={currentStats.precision.toFixed(4)} />
                  <StatBox label="Recall" value={currentStats.recall.toFixed(4)} />
                  <StatBox label="F1 Score" value={currentStats.f1.toFixed(4)} highlight />
                  <StatBox label="FPR" value={currentStats.fpr.toFixed(4)} />
                </div>
              )}
            </div>
          </Card>

          {/* Threshold comparison table */}
          <Card title="Threshold Comparison">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {["Threshold", "Precision", "Recall", "F1", "FPR", "Accuracy"].map(
                      (h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {comparisonThresholds.map((pt) => {
                    const isActive = Math.abs(pt.threshold - threshold) < 0.015;
                    const isOptimalF1 =
                      Math.abs(pt.threshold - result.optimal_f1_threshold) < 0.015;
                    return (
                      <tr
                        key={pt.threshold}
                        className={
                          isActive
                            ? "bg-brand-50"
                            : isOptimalF1
                              ? "bg-green-50"
                              : "hover:bg-gray-50"
                        }
                        onClick={() => setThreshold(pt.threshold)}
                        style={{ cursor: "pointer" }}
                      >
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 font-mono">
                          {pt.threshold.toFixed(2)}
                          {isOptimalF1 && (
                            <span className="ml-2 rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">
                              Best F1
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                          {pt.precision.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                          {pt.recall.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 font-mono">
                          {pt.f1.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                          {pt.fpr.toFixed(4)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700 font-mono">
                          {pt.accuracy.toFixed(4)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
