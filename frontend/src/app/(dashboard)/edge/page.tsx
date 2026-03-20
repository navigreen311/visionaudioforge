"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ALL_FORMATS = [
  { id: "onnx", label: "ONNX", available: true },
  { id: "tensorrt", label: "TensorRT", available: false },
  { id: "openvino", label: "OpenVINO", available: false },
  { id: "coreml", label: "CoreML", available: false },
  { id: "tflite", label: "TFLite", available: false },
  { id: "webgpu", label: "WebGPU", available: false },
];

const OPT_LEVELS = ["none", "basic", "aggressive"];

interface ExportResult {
  export_id: string;
  exports: Record<string, any>;
  total_size_mb: number;
  status: string;
}

interface BenchmarkResult {
  avg_ms: number;
  p95_ms: number;
  throughput_per_s: number;
}

interface PackageResult {
  package_id: string;
  format: string;
  size_mb: number;
  includes: string[];
}

export default function EdgePage() {
  const [modelId, setModelId] = useState("my-model");
  const [selectedFormats, setSelectedFormats] = useState<string[]>(["onnx"]);
  const [optLevel, setOptLevel] = useState("basic");
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<ExportResult | null>(null);

  const [benchmarking, setBenchmarking] = useState(false);
  const [benchmarkResult, setBenchmarkResult] = useState<BenchmarkResult | null>(null);
  const [benchIterations, setBenchIterations] = useState(100);

  const [packaging, setPackaging] = useState(false);
  const [packageResult, setPackageResult] = useState<PackageResult | null>(null);
  const [packageFormat, setPackageFormat] = useState("onnx");

  const [error, setError] = useState<string | null>(null);

  const toggleFormat = (id: string) => {
    setSelectedFormats((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]
    );
  };

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    setExportResult(null);
    try {
      const res = await fetch(`${API}/api/edge/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_id: modelId,
          formats: selectedFormats,
          optimization_level: optLevel,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setExportResult(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setExporting(false);
    }
  };

  const handleBenchmark = async () => {
    if (!exportResult) return;
    setBenchmarking(true);
    setBenchmarkResult(null);
    try {
      const res = await fetch(`${API}/api/edge/benchmark`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          export_id: exportResult.export_id,
          iterations: benchIterations,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setBenchmarkResult(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBenchmarking(false);
    }
  };

  const handlePackage = async () => {
    setPackaging(true);
    setPackageResult(null);
    try {
      const res = await fetch(`${API}/api/edge/package`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId, format: packageFormat }),
      });
      if (!res.ok) throw new Error(await res.text());
      setPackageResult(await res.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPackaging(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Edge Deployment</h1>
        <p className="mt-1 text-sm text-gray-500">
          Export models to ONNX and other edge formats for optimized inference.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}

      {/* ---- Export Section ---- */}
      <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Export Model</h2>

        {/* Model selector */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Model ID
          </label>
          <input
            type="text"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            className="w-full max-w-md rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
            placeholder="Enter model ID..."
          />
        </div>

        {/* Format checkboxes */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Export Formats
          </label>
          <div className="flex flex-wrap gap-3">
            {ALL_FORMATS.map((fmt) => (
              <label
                key={fmt.id}
                className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm cursor-pointer transition-colors ${
                  selectedFormats.includes(fmt.id)
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-200 bg-gray-50 text-gray-600"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedFormats.includes(fmt.id)}
                  onChange={() => toggleFormat(fmt.id)}
                  className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                />
                {fmt.label}
                <span
                  className={`ml-1 inline-block h-2 w-2 rounded-full ${
                    fmt.available ? "bg-green-400" : "bg-gray-300"
                  }`}
                  title={fmt.available ? "Available" : "Stub — requires additional setup"}
                />
              </label>
            ))}
          </div>
        </div>

        {/* Optimization level */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Optimization Level
          </label>
          <select
            value={optLevel}
            onChange={(e) => setOptLevel(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
          >
            {OPT_LEVELS.map((lvl) => (
              <option key={lvl} value={lvl}>
                {lvl.charAt(0).toUpperCase() + lvl.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleExport}
          disabled={exporting || selectedFormats.length === 0}
          className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {exporting ? "Exporting..." : "Export"}
        </button>

        {/* Results table */}
        {exportResult && (
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Export Results
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 px-3 font-medium text-gray-600">
                      Format
                    </th>
                    <th className="text-left py-2 px-3 font-medium text-gray-600">
                      Status
                    </th>
                    <th className="text-left py-2 px-3 font-medium text-gray-600">
                      Size (MB)
                    </th>
                    <th className="text-left py-2 px-3 font-medium text-gray-600">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(exportResult.exports).map(([fmt, data]) => (
                    <tr key={fmt} className="border-b border-gray-100">
                      <td className="py-2 px-3 font-medium">{fmt.toUpperCase()}</td>
                      <td className="py-2 px-3">
                        <span
                          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                            data.status === "stub"
                              ? "bg-yellow-100 text-yellow-700"
                              : data.path
                              ? "bg-green-100 text-green-700"
                              : "bg-red-100 text-red-700"
                          }`}
                        >
                          {data.status === "stub"
                            ? "Stub"
                            : data.path
                            ? "Exported"
                            : "Error"}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        {data.size_mb ? `${data.size_mb}` : "-"}
                      </td>
                      <td className="py-2 px-3">
                        {data.path && (
                          <a
                            href={`${API}/api/edge/exports/${exportResult.export_id}/download?format=${fmt}`}
                            className="text-brand-600 hover:underline text-xs"
                          >
                            Download
                          </a>
                        )}
                        {data.note && (
                          <span
                            className="text-xs text-gray-400 ml-2"
                            title={data.note}
                          >
                            (hover for info)
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-xs text-gray-500">
              Total size: {exportResult.total_size_mb} MB
            </p>
          </div>
        )}
      </section>

      {/* ---- Edge Package Section ---- */}
      <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Edge Package
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Generate a deployment package including the model, config, requirements,
          and sample inference code.
        </p>
        <div className="flex items-end gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Format
            </label>
            <select
              value={packageFormat}
              onChange={(e) => setPackageFormat(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
            >
              {ALL_FORMATS.map((fmt) => (
                <option key={fmt.id} value={fmt.id}>
                  {fmt.label}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={handlePackage}
            disabled={packaging}
            className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {packaging ? "Generating..." : "Generate Package"}
          </button>
        </div>

        {packageResult && (
          <div className="rounded-lg bg-gray-50 border border-gray-200 p-4">
            <p className="text-sm font-medium text-gray-700 mb-2">
              Package ID: {packageResult.package_id}
            </p>
            <p className="text-sm text-gray-600">
              Format: {packageResult.format} | Size: {packageResult.size_mb} MB
            </p>
            <p className="text-sm text-gray-600 mt-1">
              Includes:{" "}
              {packageResult.includes.map((f) => (
                <span
                  key={f}
                  className="inline-block bg-gray-200 rounded px-2 py-0.5 text-xs mr-1"
                >
                  {f}
                </span>
              ))}
            </p>
          </div>
        )}
      </section>

      {/* ---- Benchmark Section ---- */}
      <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Inference Benchmark
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Run inference benchmarks on an exported ONNX model. Export a model first.
        </p>
        <div className="flex items-end gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Iterations
            </label>
            <input
              type="number"
              value={benchIterations}
              onChange={(e) => setBenchIterations(Number(e.target.value))}
              min={1}
              max={10000}
              className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none"
            />
          </div>
          <button
            onClick={handleBenchmark}
            disabled={benchmarking || !exportResult}
            className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {benchmarking ? "Running..." : "Run Benchmark"}
          </button>
        </div>

        {benchmarkResult && (
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-blue-50 border border-blue-200 p-4 text-center">
              <p className="text-2xl font-bold text-blue-700">
                {benchmarkResult.avg_ms}
              </p>
              <p className="text-xs text-blue-500 mt-1">Avg Latency (ms)</p>
            </div>
            <div className="rounded-lg bg-purple-50 border border-purple-200 p-4 text-center">
              <p className="text-2xl font-bold text-purple-700">
                {benchmarkResult.p95_ms}
              </p>
              <p className="text-xs text-purple-500 mt-1">P95 Latency (ms)</p>
            </div>
            <div className="rounded-lg bg-green-50 border border-green-200 p-4 text-center">
              <p className="text-2xl font-bold text-green-700">
                {benchmarkResult.throughput_per_s}
              </p>
              <p className="text-xs text-green-500 mt-1">Throughput (infer/s)</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
