"use client";

import React, { useCallback, useMemo, useState } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

/* ------------------------------------------------------------------ */
/* Public types                                                        */
/* ------------------------------------------------------------------ */

export interface MFCCCoefficient {
  mean: number;
  std: number;
  values: number[];
}

export interface MFCCControls {
  n_mfcc: number;
  showDeltas: boolean;
  normalize: boolean;
}

interface MFCCHeatmapProps {
  imageSrc: string | null;
  coefficients: MFCCCoefficient[] | null;
  onCoefficientSelect: (index: number) => void;
  /** Called when the user changes MFCC params and clicks re-analyze */
  onControlsChange?: (controls: MFCCControls) => void;
  /** URL for the MFCC .npy export endpoint */
  exportNpyUrl?: string;
  loading?: boolean;
}

const N_MFCC_OPTIONS = [13, 20, 40] as const;

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function MFCCHeatmap({
  imageSrc,
  coefficients,
  onCoefficientSelect,
  onControlsChange,
  exportNpyUrl = "/api/audio/export-mfcc",
  loading = false,
}: MFCCHeatmapProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [nMfcc, setNMfcc] = useState<number>(13);
  const [showDeltas, setShowDeltas] = useState(false);
  const [normalize, setNormalize] = useState(false);

  const handleSelect = useCallback(
    (index: number) => {
      setSelectedIndex(index);
      onCoefficientSelect(index);
    },
    [onCoefficientSelect],
  );

  const handleApplyControls = useCallback(() => {
    onControlsChange?.({ n_mfcc: nMfcc, showDeltas, normalize });
  }, [nMfcc, showDeltas, normalize, onControlsChange]);

  /* ----- Export: Download as CSV (client-side) ----- */
  const handleDownloadCSV = useCallback(() => {
    if (!coefficients || coefficients.length === 0) return;

    const maxLen = Math.max(...coefficients.map((c) => c.values.length));
    const header = ["coefficient", "mean", "std", ...Array.from({ length: maxLen }, (_, i) => `t${i}`)];
    const rows = coefficients.map((c, i) => [
      `C${i}`,
      c.mean.toFixed(6),
      c.std.toFixed(6),
      ...c.values.map((v) => v.toFixed(6)),
    ]);

    const csv = [header.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "mfcc_coefficients.csv";
    a.click();
    URL.revokeObjectURL(url);
  }, [coefficients]);

  /* ----- Export: Download .npy via POST ----- */
  const handleDownloadNpy = useCallback(async () => {
    try {
      const response = await fetch(exportNpyUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n_mfcc: nMfcc, normalize, showDeltas }),
      });
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "mfcc.npy";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Silently fail — in production, surface via toast/notification
    }
  }, [exportNpyUrl, nMfcc, normalize, showDeltas]);

  /* ----- Export: Copy feature vector to clipboard ----- */
  const featureVector = useMemo(() => {
    if (!coefficients || coefficients.length === 0) return "";
    return coefficients.map((c) => c.mean.toFixed(6)).join(", ");
  }, [coefficients]);

  const handleCopyFeatureVector = useCallback(async () => {
    if (!featureVector) return;
    try {
      await navigator.clipboard.writeText(featureVector);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = featureVector;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
  }, [featureVector]);

  /* ----- Empty state ----- */
  if (!imageSrc && !coefficients) {
    return (
      <Card title="MFCC Heatmap">
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <svg
            className="mb-3 h-12 w-12"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z"
            />
          </svg>
          <p className="text-sm font-medium">No MFCC data available</p>
          <p className="mt-1 text-xs">Run MFCC analysis on an audio file to view</p>
        </div>
      </Card>
    );
  }

  return (
    <Card title="MFCC Heatmap">
      <div className="space-y-4">
        {/* Controls */}
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              n_mfcc
            </label>
            <select
              value={nMfcc}
              onChange={(e) => setNMfcc(Number(e.target.value))}
              className="rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm text-gray-700 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {N_MFCC_OPTIONS.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>

          <ToggleControl
            label="Show Deltas"
            checked={showDeltas}
            onChange={setShowDeltas}
          />
          <ToggleControl
            label="Normalize"
            checked={normalize}
            onChange={setNormalize}
          />

          {onControlsChange && (
            <Button size="sm" onClick={handleApplyControls}>
              Re-analyze
            </Button>
          )}
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <svg
              className="animate-spin h-8 w-8 text-brand-500"
              xmlns="http://www.w3.org/2000/svg"
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
            <span className="ml-3 text-sm text-gray-500">Computing MFCCs...</span>
          </div>
        )}

        {/* Heatmap image */}
        {!loading && imageSrc && (
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-gray-900">
            <img
              src={imageSrc}
              alt="MFCC Heatmap"
              className="w-full object-contain"
              draggable={false}
            />
          </div>
        )}

        {/* Coefficient cards */}
        {!loading && coefficients && coefficients.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {coefficients.map((coeff, index) => (
              <CoefficientCard
                key={index}
                index={index}
                coefficient={coeff}
                selected={selectedIndex === index}
                onClick={() => handleSelect(index)}
              />
            ))}
          </div>
        )}

        {/* Export buttons */}
        {!loading && coefficients && coefficients.length > 0 && (
          <div className="flex flex-wrap gap-2 border-t border-gray-200 pt-3">
            <Button size="sm" variant="secondary" onClick={handleDownloadNpy}>
              Download MFCC (.npy)
            </Button>
            <Button size="sm" variant="secondary" onClick={handleDownloadCSV}>
              Download as CSV
            </Button>
            <Button size="sm" variant="ghost" onClick={handleCopyFeatureVector}>
              Copy Feature Vector
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

interface CoefficientCardProps {
  index: number;
  coefficient: MFCCCoefficient;
  selected: boolean;
  onClick: () => void;
}

function CoefficientCard({ index, coefficient, selected, onClick }: CoefficientCardProps) {
  const { mean, std, values } = coefficient;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border p-3 text-left transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 ${
        selected
          ? "border-brand-500 bg-brand-50 ring-1 ring-brand-500"
          : "border-gray-200 bg-white"
      }`}
    >
      <p className="text-xs font-semibold text-gray-900">C{index}</p>
      <div className="mt-1 space-y-0.5">
        <p className="text-xs text-gray-500">
          Mean: <span className="tabular-nums font-medium text-gray-700">{mean.toFixed(3)}</span>
        </p>
        <p className="text-xs text-gray-500">
          Std: <span className="tabular-nums font-medium text-gray-700">{std.toFixed(3)}</span>
        </p>
      </div>
      {/* Mini sparkline */}
      {values.length > 0 && <Sparkline values={values} selected={selected} />}
    </button>
  );
}

function Sparkline({ values, selected }: { values: number[]; selected: boolean }) {
  const width = 80;
  const height = 24;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1 || 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="mt-1.5 w-full"
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke={selected ? "#6366f1" : "#9ca3af"}
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

interface ToggleControlProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function ToggleControl({ label, checked, onChange }: ToggleControlProps) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <div className="relative">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only"
        />
        <div
          className={`h-5 w-9 rounded-full transition-colors ${
            checked ? "bg-brand-600" : "bg-gray-300"
          }`}
        />
        <div
          className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${
            checked ? "translate-x-4" : "translate-x-0"
          }`}
        />
      </div>
      <span className="text-xs font-medium text-gray-600">{label}</span>
    </label>
  );
}
