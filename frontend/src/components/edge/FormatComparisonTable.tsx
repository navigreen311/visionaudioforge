"use client";

import { API_BASE_URL } from "@/lib/api";

import { useEffect, useState } from "react";

const API = API_BASE_URL;

interface FormatEstimate {
  format: string;
  estSizeMb: number;
  estLatencyMs: number;
  compatibility: string;
  compression: string;
}

interface FormatComparisonTableProps {
  formats: string[];
}

// Static fallback estimates when the backend is unavailable
const FALLBACK_ESTIMATES: Record<string, FormatEstimate> = {
  onnx: { format: "ONNX", estSizeMb: 42.5, estLatencyMs: 12.3, compatibility: "Universal", compression: "None" },
  tensorrt: { format: "TensorRT", estSizeMb: 28.1, estLatencyMs: 3.2, compatibility: "NVIDIA GPU", compression: "FP16" },
  coreml: { format: "CoreML", estSizeMb: 38.7, estLatencyMs: 8.5, compatibility: "Apple (iOS/macOS)", compression: "None" },
  tflite: { format: "TFLite", estSizeMb: 11.2, estLatencyMs: 18.7, compatibility: "Mobile / Edge", compression: "Quantized" },
  openvino: { format: "OpenVINO", estSizeMb: 40.1, estLatencyMs: 6.8, compatibility: "Intel CPU/GPU/VPU", compression: "FP32" },
  webgpu: { format: "WebGPU", estSizeMb: 44.0, estLatencyMs: 15.0, compatibility: "Modern Browsers", compression: "None" },
};

export default function FormatComparisonTable({ formats }: FormatComparisonTableProps) {
  const [estimates, setEstimates] = useState<FormatEstimate[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (formats.length < 2) {
      setEstimates([]);
      return;
    }

    let cancelled = false;

    const fetchEstimates = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        formats.forEach((f) => params.append("formats", f));
        const res = await fetch(`${API}/api/edge/format-estimates?${params.toString()}`);
        if (!res.ok) throw new Error("API unavailable");
        const data: FormatEstimate[] = await res.json();
        if (!cancelled) setEstimates(data);
      } catch {
        // Use fallback estimates
        if (!cancelled) {
          setEstimates(
            formats
              .map((f) => FALLBACK_ESTIMATES[f])
              .filter((e): e is FormatEstimate => e !== undefined)
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchEstimates();
    return () => { cancelled = true; };
  }, [formats]);

  if (formats.length < 2) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Format Comparison
      </h3>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading estimates...
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 px-3 font-medium text-gray-600">Format</th>
                <th className="text-left py-2 px-3 font-medium text-gray-600">Est. Size (MB)</th>
                <th className="text-left py-2 px-3 font-medium text-gray-600">Est. Latency (ms)</th>
                <th className="text-left py-2 px-3 font-medium text-gray-600">Compatibility</th>
                <th className="text-left py-2 px-3 font-medium text-gray-600">Compression</th>
              </tr>
            </thead>
            <tbody>
              {estimates.map((est) => {
                const isBestSize = est.estSizeMb === Math.min(...estimates.map((e) => e.estSizeMb));
                const isBestLatency = est.estLatencyMs === Math.min(...estimates.map((e) => e.estLatencyMs));

                return (
                  <tr key={est.format} className="border-b border-gray-100">
                    <td className="py-2 px-3 font-medium text-gray-800">
                      {est.format}
                    </td>
                    <td className={`py-2 px-3 ${isBestSize ? "text-green-600 font-semibold" : "text-gray-700"}`}>
                      {est.estSizeMb.toFixed(1)}
                    </td>
                    <td className={`py-2 px-3 ${isBestLatency ? "text-green-600 font-semibold" : "text-gray-700"}`}>
                      {est.estLatencyMs.toFixed(1)}
                    </td>
                    <td className="py-2 px-3 text-gray-600">{est.compatibility}</td>
                    <td className="py-2 px-3">
                      <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                        {est.compression}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
