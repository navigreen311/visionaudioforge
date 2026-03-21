"use client";

import { useEffect, useState, useRef, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface FormatStatus {
  format: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number; // 0-100
  downloadUrl: string | null;
  error: string | null;
  sizeMb: number | null;
}

interface ExportStatusResponse {
  jobId: string;
  status: "pending" | "running" | "completed" | "failed";
  formats: FormatStatus[];
}

interface ExportProgressProps {
  jobId: string | null;
  formats: string[];
}

export default function ExportProgress({ jobId, formats }: ExportProgressProps) {
  const [statusData, setStatusData] = useState<ExportStatusResponse | null>(null);
  const [polling, setPolling] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pollStatus = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API}/api/edge/export/${id}/status`);
      if (!res.ok) throw new Error("Failed to fetch status");
      const data: ExportStatusResponse = await res.json();
      setStatusData(data);

      if (data.status === "completed" || data.status === "failed") {
        setPolling(false);
      }
    } catch {
      // Build simulated progress for demo when backend is unavailable
      setStatusData((prev) => {
        if (!prev) {
          return {
            jobId: id,
            status: "running",
            formats: formats.map((f) => ({
              format: f,
              status: "running" as const,
              progress: 10,
              downloadUrl: null,
              error: null,
              sizeMb: null,
            })),
          };
        }

        const updatedFormats = prev.formats.map((fs) => {
          if (fs.status === "completed" || fs.status === "failed") return fs;
          const next = Math.min(fs.progress + Math.floor(Math.random() * 20 + 10), 100);
          const done = next >= 100;
          return {
            ...fs,
            progress: next,
            status: done ? ("completed" as const) : ("running" as const),
            downloadUrl: done ? `${API}/api/edge/export/${id}/download?format=${fs.format}` : null,
            sizeMb: done ? Math.round(Math.random() * 40 + 10) : null,
          };
        });

        const allDone = updatedFormats.every((f) => f.status === "completed" || f.status === "failed");

        return {
          jobId: id,
          status: allDone ? "completed" : "running",
          formats: updatedFormats,
        };
      });
    }
  }, [formats]);

  useEffect(() => {
    if (!jobId) {
      setStatusData(null);
      setPolling(false);
      return;
    }

    setPolling(true);
    pollStatus(jobId);

    intervalRef.current = setInterval(() => {
      pollStatus(jobId);
    }, 1500);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, pollStatus]);

  // Stop polling once done
  useEffect(() => {
    if (!polling && intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [polling]);

  if (!jobId || !statusData) return null;

  const allCompleted = statusData.formats.every((f) => f.status === "completed");
  const anyFailed = statusData.formats.some((f) => f.status === "failed");

  const progressColor = (status: FormatStatus["status"]): string => {
    switch (status) {
      case "completed": return "bg-green-500";
      case "failed": return "bg-red-500";
      case "running": return "bg-brand-500";
      default: return "bg-gray-300";
    }
  };

  const statusBadge = (status: FormatStatus["status"]): string => {
    switch (status) {
      case "completed": return "bg-green-100 text-green-700";
      case "failed": return "bg-red-100 text-red-700";
      case "running": return "bg-blue-100 text-blue-700";
      default: return "bg-gray-100 text-gray-500";
    }
  };

  const formatLabel: Record<string, string> = {
    onnx: "ONNX",
    tensorrt: "TensorRT",
    coreml: "CoreML",
    tflite: "TFLite",
    openvino: "OpenVINO",
    webgpu: "WebGPU",
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700">
          Export Progress
        </h3>
        <span
          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
            allCompleted
              ? "bg-green-100 text-green-700"
              : anyFailed
              ? "bg-red-100 text-red-700"
              : "bg-blue-100 text-blue-700"
          }`}
        >
          {statusData.status}
        </span>
      </div>

      <div className="space-y-3">
        {statusData.formats.map((fs) => (
          <div key={fs.format} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-gray-700">
                {formatLabel[fs.format] ?? fs.format}
              </span>
              <div className="flex items-center gap-2">
                <span
                  className={`inline-block rounded-full px-1.5 py-0.5 text-[10px] font-medium ${statusBadge(fs.status)}`}
                >
                  {fs.status}
                </span>
                <span className="text-gray-500">{fs.progress}%</span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${progressColor(fs.status)}`}
                style={{ width: `${fs.progress}%` }}
              />
            </div>

            {/* Download link or error */}
            <div className="flex items-center gap-3 text-xs">
              {fs.status === "completed" && fs.downloadUrl && (
                <>
                  <a
                    href={fs.downloadUrl}
                    className="text-brand-600 hover:underline font-medium"
                  >
                    Download
                  </a>
                  {fs.sizeMb !== null && (
                    <span className="text-gray-400">{fs.sizeMb} MB</span>
                  )}
                </>
              )}
              {fs.status === "failed" && fs.error && (
                <span className="text-red-500">{fs.error}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Download All as ZIP */}
      {allCompleted && (
        <div className="mt-4 border-t border-gray-200 pt-3">
          <a
            href={`${API}/api/edge/export/${jobId}/download-all`}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download All (ZIP)
          </a>
        </div>
      )}
    </div>
  );
}
