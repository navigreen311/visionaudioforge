"use client";

import React, { useState, useCallback } from "react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import FileUpload from "@/components/ui/FileUpload";
import FeatureDriftTable, { type DriftFeature } from "./FeatureDriftTable";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type DriftMethod = "ks_test" | "chi_square" | "psi" | "wasserstein";
type TimeWindow = 7 | 30 | 90;

interface DriftApiResponse {
  overall_psi: number;
  status: "stable" | "minor" | "major";
  features: DriftFeature[];
  method: string;
  threshold: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const DRIFT_METHODS: { value: DriftMethod; label: string }[] = [
  { value: "ks_test", label: "KS Test" },
  { value: "chi_square", label: "Chi-Square" },
  { value: "psi", label: "PSI" },
  { value: "wasserstein", label: "Wasserstein" },
];

const STATUS_CONFIG: Record<string, { label: string; variant: string }> = {
  stable: { label: "Stable", variant: "success" },
  minor: { label: "Minor Drift", variant: "warning" },
  major: { label: "Major Drift", variant: "error" },
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function DriftDetectionTab() {
  // File state
  const [refFile, setRefFile] = useState<File | null>(null);
  const [curFile, setCurFile] = useState<File | null>(null);

  // Production data toggle
  const [useProdData, setUseProdData] = useState(false);
  const [prodWindow, setProdWindow] = useState<TimeWindow>(7);

  // Parameters
  const [featureNames, setFeatureNames] = useState("");
  const [method, setMethod] = useState<DriftMethod>("psi");
  const [threshold, setThreshold] = useState(0.1);

  // Results
  const [result, setResult] = useState<DriftApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRefFiles = useCallback(
    (files: File[]) => setRefFile(files[0] ?? null),
    [],
  );
  const handleCurFiles = useCallback(
    (files: File[]) => setCurFile(files[0] ?? null),
    [],
  );

  const handleRunAnalysis = async () => {
    setError(null);

    if (!useProdData && (!refFile || !curFile)) {
      setError(
        "Please upload both Reference and Current data CSV files, or enable production data.",
      );
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();

      if (useProdData) {
        formData.append("use_prod_data", "true");
        formData.append("prod_window_days", String(prodWindow));
      } else {
        if (refFile) formData.append("reference_file", refFile);
        if (curFile) formData.append("current_file", curFile);
      }

      if (featureNames.trim()) {
        formData.append("feature_names", featureNames.trim());
      }
      formData.append("method", method);
      formData.append("threshold", String(threshold));

      const resp = await fetch(`${API_BASE}/api/validate/drift`, {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Request failed (${resp.status})`);
      }

      const data: DriftApiResponse = await resp.json();
      setResult(data);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Drift analysis request failed",
      );
    } finally {
      setLoading(false);
    }
  };

  const statusCfg = result
    ? (STATUS_CONFIG[result.status] ?? STATUS_CONFIG.stable)
    : null;

  return (
    <div className="space-y-6">
      {/* ---- Upload Section ---- */}
      <Card title="Data Sources">
        {/* Production data toggle */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <label className="relative inline-flex cursor-pointer items-center">
            <input
              type="checkbox"
              checked={useProdData}
              onChange={(e) => setUseProdData(e.target.checked)}
              className="peer sr-only"
            />
            <div className="h-5 w-9 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-4 after:w-4 after:rounded-full after:bg-white after:transition-all peer-checked:bg-brand-600 peer-checked:after:translate-x-full" />
          </label>
          <span className="text-sm text-gray-700">Use production data</span>
          {useProdData && (
            <select
              value={prodWindow}
              onChange={(e) =>
                setProdWindow(Number(e.target.value) as TimeWindow)
              }
              className="ml-2 rounded-md border border-gray-300 px-2 py-1 text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          )}
        </div>

        {!useProdData && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-sm font-medium text-gray-700">
                Reference Data CSV
              </p>
              <FileUpload accept=".csv" onFiles={handleRefFiles} />
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-gray-700">
                Current Data CSV
              </p>
              <FileUpload accept=".csv" onFiles={handleCurFiles} />
            </div>
          </div>
        )}
      </Card>

      {/* ---- Parameters Section ---- */}
      <Card title="Analysis Parameters">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Feature names */}
          <div className="sm:col-span-2 lg:col-span-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Feature Names{" "}
              <span className="text-gray-400">
                (comma-separated, optional)
              </span>
            </label>
            <input
              type="text"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="feature_a, feature_b, feature_c"
              value={featureNames}
              onChange={(e) => setFeatureNames(e.target.value)}
            />
          </div>

          {/* Drift method */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Drift Method
            </label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value as DriftMethod)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              {DRIFT_METHODS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          {/* Alert threshold */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Alert Threshold:{" "}
              <span className="font-mono">{threshold.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min={0.05}
              max={0.5}
              step={0.01}
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="w-full accent-brand-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-0.5">
              <span>0.05</span>
              <span>0.50</span>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <Button
            onClick={handleRunAnalysis}
            disabled={loading}
            loading={loading}
          >
            {loading ? "Running..." : "Run Drift Analysis"}
          </Button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </Card>

      {/* ---- Results Section ---- */}
      {result && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Card title="Overall PSI Score">
              <p className="text-3xl font-bold text-gray-900">
                {result.overall_psi.toFixed(4)}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                Method: {result.method} &middot; Threshold: {result.threshold}
              </p>
            </Card>
            <Card title="Drift Status">
              <div className="flex items-center gap-3">
                {statusCfg && (
                  <Badge
                    variant={statusCfg.variant}
                    className="text-base px-4 py-1"
                  >
                    {statusCfg.label}
                  </Badge>
                )}
              </div>
              <p className="mt-2 text-sm text-gray-600">
                {result.features.filter((f) => f.status === "major").length}{" "}
                features with major drift,{" "}
                {result.features.filter((f) => f.status === "minor").length}{" "}
                with minor drift.
              </p>
            </Card>
          </div>

          <Card title="Feature Drift Details">
            <FeatureDriftTable features={result.features} />
          </Card>
        </>
      )}
    </div>
  );
}
