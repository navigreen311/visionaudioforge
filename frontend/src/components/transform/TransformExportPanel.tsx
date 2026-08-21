"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";

interface TransformExportPanelProps {
  outputB64?: string;
  outputFilename?: string;
  onChainTransform?: () => void;
  isVisible: boolean;
}

export default function TransformExportPanel({
  outputB64,
  outputFilename = "output",
  onChainTransform,
  isVisible,
}: TransformExportPanelProps) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleDownload = useCallback(() => {
    if (!outputB64) return;

    // Detect mime from base64 header or default to octet-stream
    let dataUrl = outputB64;
    if (!outputB64.startsWith("data:")) {
      dataUrl = `data:application/octet-stream;base64,${outputB64}`;
    }

    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = outputFilename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [outputB64, outputFilename]);

  const handleSaveToAssets = useCallback(async () => {
    if (!outputB64) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      const res = await fetch("/api/assets/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: outputFilename,
          data: outputB64,
        }),
      });

      if (!res.ok) {
        throw new Error(`Save failed (${res.status})`);
      }

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [outputB64, outputFilename]);

  const handleSendToPipeline = useCallback(() => {
    router.push("/pipeline");
  }, [router]);

  if (!isVisible || !outputB64) return null;

  return (
    <div className="w-full rounded-lg border border-gray-200 bg-white p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-800">Export Result</h3>

      <div className="flex flex-wrap gap-2">
        {/* Download Output */}
        <button
          type="button"
          onClick={handleDownload}
          className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
          style={{ backgroundColor: "#185FA5" }}
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          Download Output
        </button>

        {/* Save to Assets */}
        <button
          type="button"
          onClick={handleSaveToAssets}
          disabled={saving}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? (
            <svg
              className="h-4 w-4 animate-spin"
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
          ) : (
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
              />
            </svg>
          )}
          Save to Assets
        </button>

        {/* Send to Pipeline */}
        <button
          type="button"
          onClick={handleSendToPipeline}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M13 5l7 7-7 7M5 5l7 7-7 7"
            />
          </svg>
          Send to Pipeline
        </button>

        {/* Apply Another Transform */}
        {onChainTransform && (
          <button
            type="button"
            onClick={onChainTransform}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Apply Another Transform
          </button>
        )}
      </div>

      {/* Status messages */}
      {saveSuccess && (
        <p className="text-xs text-green-600 font-medium">
          Saved to assets successfully.
        </p>
      )}
      {saveError && (
        <p className="text-xs text-red-600 font-medium">{saveError}</p>
      )}
    </div>
  );
}
