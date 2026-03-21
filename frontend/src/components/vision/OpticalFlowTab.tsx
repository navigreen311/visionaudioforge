"use client";

import React, { useState, useCallback } from "react";
import api from "@/lib/api";
import ImageUploadPreview from "./ImageUploadPreview";
import StatsPanel from "./StatsPanel";

// ── Types ──────────────────────────────────────────────────────────

type FlowMethod = "lk" | "farneback" | "both";

interface LKParams {
  maxCorners: number;
  qualityLevel: number;
  minDistance: number;
  windowSize: number;
}

interface FarnebackParams {
  pyramidLevels: number;
  windowSize: number;
  iterations: number;
}

interface FlowStats {
  meanMagnitude: number;
  maxMagnitude: number;
  trackedPoints: number;
  coveragePct: number;
}

interface FlowResponse {
  flow_image?: string;
  stats?: FlowStats;
  lk_image?: string;
  farneback_image?: string;
  lk_stats?: FlowStats;
  farneback_stats?: FlowStats;
  [key: string]: unknown;
}

// ── Defaults ───────────────────────────────────────────────────────

const DEFAULT_LK: LKParams = {
  maxCorners: 100,
  qualityLevel: 0.3,
  minDistance: 7,
  windowSize: 15,
};

const DEFAULT_FARNEBACK: FarnebackParams = {
  pyramidLevels: 3,
  windowSize: 15,
  iterations: 3,
};

// ── Loading Skeleton ───────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="text-sm font-medium text-gray-500">
        Processing optical flow analysis...
      </div>
      {/* Image skeleton */}
      <div className="h-64 w-full rounded-lg bg-gray-200" />
      {/* Stats skeleton */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="mb-3 h-4 w-24 rounded bg-gray-200" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-1">
              <div className="h-3 w-16 rounded bg-gray-200" />
              <div className="h-4 w-20 rounded bg-gray-200" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Component ──────────────────────────────────────────────────────

export default function OpticalFlowTab() {
  const [frame1, setFrame1] = useState<File | null>(null);
  const [frame2, setFrame2] = useState<File | null>(null);
  const [method, setMethod] = useState<FlowMethod>("farneback");
  const [lkParams, setLkParams] = useState<LKParams>(DEFAULT_LK);
  const [farnebackParams, setFarnebackParams] =
    useState<FarnebackParams>(DEFAULT_FARNEBACK);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FlowResponse | null>(null);

  const handleFrame1 = useCallback((file: File) => setFrame1(file), []);
  const handleFrame2 = useCallback((file: File) => setFrame2(file), []);

  const handleAnalyze = useCallback(async () => {
    if (!frame1 || !frame2) {
      setError("Please upload both frames before analyzing.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("frame1", frame1);
      formData.append("frame2", frame2);
      formData.append("method", method);

      const params: Record<string, unknown> = {};
      if (method === "lk" || method === "both") {
        params.lk = {
          max_corners: lkParams.maxCorners,
          quality_level: lkParams.qualityLevel,
          min_distance: lkParams.minDistance,
          window_size: lkParams.windowSize,
        };
      }
      if (method === "farneback" || method === "both") {
        params.farneback = {
          pyramid_levels: farnebackParams.pyramidLevels,
          window_size: farnebackParams.windowSize,
          iterations: farnebackParams.iterations,
        };
      }
      formData.append("params", JSON.stringify(params));

      const { data } = await api.post<FlowResponse>(
        "/api/vision/optical-flow",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      setResult(data);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to analyze optical flow.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [frame1, frame2, method, lkParams, farnebackParams]);

  const renderStats = (stats: FlowStats, title?: string) => (
    <StatsPanel
      title={title}
      stats={[
        { label: "Mean Magnitude", value: stats.meanMagnitude },
        { label: "Max Magnitude", value: stats.maxMagnitude },
        { label: "Tracked Points", value: stats.trackedPoints },
        { label: "Coverage %", value: `${stats.coveragePct.toFixed(1)}%` },
      ]}
      className="mt-4"
    />
  );

  return (
    <div className="space-y-6">
      {/* Dual frame upload */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ImageUploadPreview
          label="Frame 1 (Previous)"
          onFile={handleFrame1}
          accept="image/*"
        />
        <ImageUploadPreview
          label="Frame 2 (Current)"
          onFile={handleFrame2}
          accept="image/*"
        />
      </div>

      {/* Method selector */}
      <fieldset>
        <legend className="mb-2 text-sm font-medium text-gray-700">
          Method
        </legend>
        <div className="flex gap-6">
          {(["lk", "farneback", "both"] as const).map((m) => (
            <label
              key={m}
              className="flex items-center gap-2 text-sm text-gray-700"
            >
              <input
                type="radio"
                name="flow-method"
                value={m}
                checked={method === m}
                onChange={() => setMethod(m)}
                className="text-brand-600 focus:ring-brand-500"
              />
              {m === "lk"
                ? "Lucas-Kanade"
                : m === "farneback"
                  ? "Farneback"
                  : "Both"}
            </label>
          ))}
        </div>
      </fieldset>

      {/* LK Controls */}
      {(method === "lk" || method === "both") && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <h4 className="mb-3 text-sm font-semibold text-gray-700">
            Lucas-Kanade Parameters
          </h4>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Max Corners
              </label>
              <input
                type="number"
                min={1}
                value={lkParams.maxCorners}
                onChange={(e) =>
                  setLkParams((p) => ({
                    ...p,
                    maxCorners: Number(e.target.value),
                  }))
                }
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Quality Level: {lkParams.qualityLevel.toFixed(2)}
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={lkParams.qualityLevel}
                onChange={(e) =>
                  setLkParams((p) => ({
                    ...p,
                    qualityLevel: Number(e.target.value),
                  }))
                }
                className="w-full"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Min Distance
              </label>
              <input
                type="number"
                min={1}
                value={lkParams.minDistance}
                onChange={(e) =>
                  setLkParams((p) => ({
                    ...p,
                    minDistance: Number(e.target.value),
                  }))
                }
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Window Size
              </label>
              <input
                type="number"
                min={3}
                step={2}
                value={lkParams.windowSize}
                onChange={(e) =>
                  setLkParams((p) => ({
                    ...p,
                    windowSize: Number(e.target.value),
                  }))
                }
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* Farneback Controls */}
      {(method === "farneback" || method === "both") && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <h4 className="mb-3 text-sm font-semibold text-gray-700">
            Farneback Parameters
          </h4>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Pyramid Levels
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={farnebackParams.pyramidLevels}
                onChange={(e) =>
                  setFarnebackParams((p) => ({
                    ...p,
                    pyramidLevels: Number(e.target.value),
                  }))
                }
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Window Size
              </label>
              <input
                type="number"
                min={3}
                step={2}
                value={farnebackParams.windowSize}
                onChange={(e) =>
                  setFarnebackParams((p) => ({
                    ...p,
                    windowSize: Number(e.target.value),
                  }))
                }
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">
                Iterations
              </label>
              <input
                type="number"
                min={1}
                max={20}
                value={farnebackParams.iterations}
                onChange={(e) =>
                  setFarnebackParams((p) => ({
                    ...p,
                    iterations: Number(e.target.value),
                  }))
                }
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* Analyze button */}
      <button
        onClick={handleAnalyze}
        disabled={loading || !frame1 || !frame2}
        className="rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Analyzing..." : "Analyze Flow"}
      </button>

      {/* Loading skeleton */}
      {loading && <LoadingSkeleton />}

      {/* Error with retry */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-700">{error}</p>
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={loading}
            className="mt-2 rounded bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
          >
            Retry
          </button>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-700">Results</h3>

          {/* Single method result */}
          {result.flow_image && (
            <img
              src={result.flow_image}
              alt="Optical flow visualization"
              className="max-w-full rounded border border-gray-200"
            />
          )}
          {result.stats && renderStats(result.stats)}

          {/* Both method results */}
          {result.lk_image && (
            <div>
              <p className="mb-2 text-sm font-medium text-gray-600">
                Lucas-Kanade
              </p>
              <img
                src={result.lk_image}
                alt="LK optical flow"
                className="max-w-full rounded border border-gray-200"
              />
              {result.lk_stats && renderStats(result.lk_stats, "LK Stats")}
            </div>
          )}
          {result.farneback_image && (
            <div>
              <p className="mb-2 text-sm font-medium text-gray-600">
                Farneback
              </p>
              <img
                src={result.farneback_image}
                alt="Farneback optical flow"
                className="max-w-full rounded border border-gray-200"
              />
              {result.farneback_stats &&
                renderStats(result.farneback_stats, "Farneback Stats")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
