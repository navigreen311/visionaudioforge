"use client";

import { API_BASE_URL } from "@/lib/api";

import React, { useState, useCallback } from "react";
import LatencyHistogram from "./LatencyHistogram";

const API = API_BASE_URL;

const FORMATS = ["onnx", "tensorrt", "tflite", "coreml", "openvino"] as const;
type Format = (typeof FORMATS)[number];

const DEVICES = ["cpu", "gpu", "auto"] as const;
type Device = (typeof DEVICES)[number];

interface BenchmarkConfig {
  model_id: string;
  format: Format;
  input_shape: string;
  iterations: number;
  warmup: number;
  device: Device;
}

interface BenchmarkSummary {
  avg_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  throughput_fps: number;
  memory_mb: number;
  speedup: string;
}

interface BenchmarkRunResult {
  benchmark_id: string;
  config: BenchmarkConfig;
  summary: BenchmarkSummary;
  latencies: number[];
  percentiles: { p50: number; p95: number; p99: number };
}

interface ComparisonEntry {
  format: string;
  summary: BenchmarkSummary;
}

export default function InferenceBenchmark() {
  const [config, setConfig] = useState<BenchmarkConfig>({
    model_id: "my-model",
    format: "onnx",
    input_shape: "1,3,224,224",
    iterations: 100,
    warmup: 10,
    device: "cpu",
  });

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BenchmarkRunResult | null>(null);
  const [comparisons, setComparisons] = useState<ComparisonEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const updateConfig = useCallback(
    <K extends keyof BenchmarkConfig>(key: K, value: BenchmarkConfig[K]) => {
      setConfig((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const handleRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API}/api/edge/benchmark`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }

      const data: BenchmarkRunResult = await res.json();
      setResult(data);

      // Add to comparisons for multi-format view
      setComparisons((prev) => {
        const filtered = prev.filter((c) => c.format !== config.format);
        return [...filtered, { format: config.format, summary: data.summary }];
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Benchmark failed";
      setError(message);
    } finally {
      setRunning(false);
    }
  }, [config]);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-800 mb-2">Inference Benchmark</h3>
      <p className="text-sm text-gray-500 mb-4">
        Run latency and throughput benchmarks across formats and devices.
      </p>

      {/* Controls */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6 mb-4">
        {/* Model ID */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Model</label>
          <input
            type="text"
            value={config.model_id}
            onChange={(e) => updateConfig("model_id", e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
          />
        </div>

        {/* Format */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Format</label>
          <select
            value={config.format}
            onChange={(e) => updateConfig("format", e.target.value as Format)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
          >
            {FORMATS.map((f) => (
              <option key={f} value={f}>
                {f.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        {/* Input Shape */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Input Shape</label>
          <input
            type="text"
            value={config.input_shape}
            onChange={(e) => updateConfig("input_shape", e.target.value)}
            placeholder="1,3,224,224"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
          />
        </div>

        {/* Iterations */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Iterations</label>
          <input
            type="number"
            value={config.iterations}
            onChange={(e) => updateConfig("iterations", Number(e.target.value))}
            min={1}
            max={10000}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
          />
        </div>

        {/* Warmup */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Warmup</label>
          <input
            type="number"
            value={config.warmup}
            onChange={(e) => updateConfig("warmup", Number(e.target.value))}
            min={0}
            max={1000}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
          />
        </div>

        {/* Device */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Device</label>
          <select
            value={config.device}
            onChange={(e) => updateConfig("device", e.target.value as Device)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
          >
            {DEVICES.map((d) => (
              <option key={d} value={d}>
                {d.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button
        type="button"
        onClick={handleRun}
        disabled={running}
        className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {running ? "Running Benchmark..." : "Run Benchmark"}
      </button>

      {/* Error */}
      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="mt-6 space-y-6">
          {/* Summary stats */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard label="Avg Latency" value={`${result.summary.avg_ms.toFixed(2)} ms`} color="blue" />
            <StatCard label="P50 Latency" value={`${result.summary.p50_ms.toFixed(2)} ms`} color="blue" />
            <StatCard label="P95 Latency" value={`${result.summary.p95_ms.toFixed(2)} ms`} color="amber" />
            <StatCard label="P99 Latency" value={`${result.summary.p99_ms.toFixed(2)} ms`} color="red" />
            <StatCard label="Throughput" value={`${result.summary.throughput_fps.toFixed(1)} fps`} color="green" />
            <StatCard label="Memory" value={`${result.summary.memory_mb.toFixed(0)} MB`} color="purple" />
          </div>

          {/* Speedup badge */}
          {result.summary.speedup && (
            <div className="inline-flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-sm font-semibold text-green-700">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3.5 w-3.5">
                <path fillRule="evenodd" d="M8 14a.75.75 0 01-.75-.75V4.56L4.03 7.78a.75.75 0 01-1.06-1.06l4.5-4.5a.75.75 0 011.06 0l4.5 4.5a.75.75 0 01-1.06 1.06L8.75 4.56v8.69A.75.75 0 018 14z" clipRule="evenodd" />
              </svg>
              {result.summary.speedup} faster
            </div>
          )}

          {/* Histogram */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Latency Distribution</h4>
            <LatencyHistogram data={result.latencies} percentiles={result.percentiles} />
          </div>

          {/* Comparison table */}
          {comparisons.length > 1 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Format Comparison</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="py-2 px-3 text-left font-medium text-gray-600">Format</th>
                      <th className="py-2 px-3 text-left font-medium text-gray-600">Avg (ms)</th>
                      <th className="py-2 px-3 text-left font-medium text-gray-600">P50 (ms)</th>
                      <th className="py-2 px-3 text-left font-medium text-gray-600">P95 (ms)</th>
                      <th className="py-2 px-3 text-left font-medium text-gray-600">P99 (ms)</th>
                      <th className="py-2 px-3 text-left font-medium text-gray-600">FPS</th>
                      <th className="py-2 px-3 text-left font-medium text-gray-600">Memory</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisons.map((c) => (
                      <tr
                        key={c.format}
                        className={`border-b border-gray-100 ${c.format === config.format ? "bg-brand-50" : ""}`}
                      >
                        <td className="py-2 px-3 font-medium">{c.format.toUpperCase()}</td>
                        <td className="py-2 px-3">{c.summary.avg_ms.toFixed(2)}</td>
                        <td className="py-2 px-3">{c.summary.p50_ms.toFixed(2)}</td>
                        <td className="py-2 px-3">{c.summary.p95_ms.toFixed(2)}</td>
                        <td className="py-2 px-3">{c.summary.p99_ms.toFixed(2)}</td>
                        <td className="py-2 px-3">{c.summary.throughput_fps.toFixed(1)}</td>
                        <td className="py-2 px-3">{c.summary.memory_mb.toFixed(0)} MB</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* StatCard sub-component                                              */
/* ------------------------------------------------------------------ */

interface StatCardProps {
  label: string;
  value: string;
  color: "blue" | "amber" | "red" | "green" | "purple";
}

const COLOR_MAP: Record<StatCardProps["color"], { bg: string; border: string; text: string; sub: string }> = {
  blue: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", sub: "text-blue-500" },
  amber: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", sub: "text-amber-500" },
  red: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", sub: "text-red-500" },
  green: { bg: "bg-green-50", border: "border-green-200", text: "text-green-700", sub: "text-green-500" },
  purple: { bg: "bg-purple-50", border: "border-purple-200", text: "text-purple-700", sub: "text-purple-500" },
};

function StatCard({ label, value, color }: StatCardProps) {
  const c = COLOR_MAP[color];
  return (
    <div className={`rounded-lg ${c.bg} border ${c.border} p-3 text-center`}>
      <p className={`text-lg font-bold ${c.text}`}>{value}</p>
      <p className={`text-xs mt-0.5 ${c.sub}`}>{label}</p>
    </div>
  );
}
