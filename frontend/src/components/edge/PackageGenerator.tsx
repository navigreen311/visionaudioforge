"use client";

import React, { useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface PackageGeneratorProps {
  modelId: string;
  format: string;
}

interface PackageFile {
  name: string;
  size_kb: number;
}

interface PackageResponse {
  package_id: string;
  model_id: string;
  format: string;
  status: string;
  files: PackageFile[];
  total_size_mb: number;
  inference_code: string;
  download_url: string;
}

type ProgressPhase = "idle" | "preparing" | "bundling" | "generating" | "done" | "error";

const PHASE_LABELS: Record<ProgressPhase, string> = {
  idle: "",
  preparing: "Preparing model artifacts...",
  bundling: "Bundling config & requirements...",
  generating: "Generating inference code...",
  done: "Package ready!",
  error: "Generation failed",
};

export default function PackageGenerator({ modelId, format }: PackageGeneratorProps) {
  const [phase, setPhase] = useState<ProgressPhase>("idle");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<PackageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    setPhase("preparing");
    setProgress(0);
    setResult(null);
    setError(null);

    // Simulate progress stages while request is in flight
    const progressTimer = window.setInterval(() => {
      setProgress((prev) => {
        if (prev < 30) {
          setPhase("preparing");
          return prev + 10;
        }
        if (prev < 60) {
          setPhase("bundling");
          return prev + 10;
        }
        if (prev < 85) {
          setPhase("generating");
          return prev + 5;
        }
        return prev;
      });
    }, 300);

    try {
      const res = await fetch(`${API}/api/edge/package`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId, format }),
      });

      clearInterval(progressTimer);

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }

      const data: PackageResponse = await res.json();
      setResult(data);
      setProgress(100);
      setPhase("done");
    } catch (err: unknown) {
      clearInterval(progressTimer);
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      setPhase("error");
    }
  }, [modelId, format]);

  const handleDownload = useCallback(() => {
    if (!result) return;
    // Trigger download via the backend URL
    const link = document.createElement("a");
    link.href = `${API}${result.download_url}`;
    link.download = `edge-package-${result.format}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [result]);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-800 mb-2">Package Generator</h3>
      <p className="text-sm text-gray-500 mb-4">
        Generate a deployment-ready package with model, config, requirements, and inference code.
      </p>

      {/* Controls */}
      <div className="flex items-center gap-4 mb-4">
        <div className="text-sm text-gray-600">
          <span className="font-medium">Model:</span> {modelId}
        </div>
        <div className="text-sm text-gray-600">
          <span className="font-medium">Format:</span> {format.toUpperCase()}
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={phase !== "idle" && phase !== "done" && phase !== "error"}
          className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {phase === "idle" || phase === "done" || phase === "error"
            ? "Generate Package"
            : "Generating..."}
        </button>
      </div>

      {/* Progress bar */}
      {phase !== "idle" && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500">{PHASE_LABELS[phase]}</span>
            <span className="text-xs font-medium text-gray-700">{progress}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-gray-200 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                phase === "error" ? "bg-red-500" : phase === "done" ? "bg-green-500" : "bg-brand-500"
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Package contents */}
      {result && (
        <div className="space-y-4">
          {/* File listing */}
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Package Contents</h4>
            <div className="space-y-1">
              {result.files.map((file) => (
                <div
                  key={file.name}
                  className="flex items-center justify-between rounded px-2 py-1 text-sm hover:bg-gray-100"
                >
                  <span className="font-mono text-gray-800">{file.name}</span>
                  <span className="text-xs text-gray-500">
                    {file.size_kb < 1024
                      ? `${file.size_kb.toFixed(1)} KB`
                      : `${(file.size_kb / 1024).toFixed(1)} MB`}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-2 border-t border-gray-200 pt-2 text-xs text-gray-500">
              Total: {result.total_size_mb.toFixed(1)} MB
            </div>
          </div>

          {/* Download button */}
          <button
            type="button"
            onClick={handleDownload}
            className="inline-flex items-center gap-2 rounded-lg border border-brand-300 bg-brand-50 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-100 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
              <path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z" />
              <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
            </svg>
            Download Package (.zip)
          </button>

          {/* Code preview */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">inference.py</h4>
            <div className="rounded-lg border border-gray-700 bg-gray-950 overflow-auto max-h-80">
              <pre className="p-4 text-xs leading-relaxed">
                {result.inference_code.split("\n").map((line, i) => (
                  <div key={i} className="flex">
                    <span className="mr-4 inline-block w-6 select-none text-right text-gray-600">
                      {i + 1}
                    </span>
                    <code className="text-green-400 font-mono">{line}</code>
                  </div>
                ))}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
