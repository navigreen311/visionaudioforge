"use client";

import React, { useState, useCallback } from "react";

interface ExportPanelProps {
  results?: Record<string, unknown>;
  processedImageB64?: string;
  isVisible: boolean;
}

function DownloadIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z" />
      <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M7 3.5A1.5 1.5 0 018.5 2h3.879a1.5 1.5 0 011.06.44l3.122 3.12A1.5 1.5 0 0117 6.622V12.5a1.5 1.5 0 01-1.5 1.5h-1v-3.379a3 3 0 00-.879-2.121L10.5 5.379A3 3 0 008.379 4.5H7v-1z" />
      <path d="M4.5 6A1.5 1.5 0 003 7.5v9A1.5 1.5 0 004.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L9.44 6.439A1.5 1.5 0 008.378 6H4.5z" />
    </svg>
  );
}

function SaveIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M9.25 13.25a.75.75 0 001.5 0V4.636l2.955 3.129a.75.75 0 001.09-1.03l-4.25-4.5a.75.75 0 00-1.09 0l-4.25 4.5a.75.75 0 101.09 1.03L9.25 4.636v8.614z" />
      <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
    </svg>
  );
}

function JsonIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path
        fillRule="evenodd"
        d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z"
        clipRule="evenodd"
      />
    </svg>
  );
}

type ToastState = { type: "success" | "error"; message: string } | null;

/**
 * Extracts key stats (dimensions, min, max, mean, std) from API results
 * for clipboard copy.
 */
function extractKeyStats(results: Record<string, unknown>): string {
  const lines: string[] = [];

  const tryAdd = (label: string, key: string) => {
    if (key in results && results[key] !== undefined) {
      lines.push(`${label}: ${String(results[key])}`);
    }
  };

  tryAdd("Width", "width");
  tryAdd("Height", "height");
  tryAdd("Dimensions", "dimensions");
  tryAdd("Min", "min");
  tryAdd("Max", "max");
  tryAdd("Mean", "mean");
  tryAdd("Std", "std");
  tryAdd("Channels", "channels");
  tryAdd("Format", "format");

  // Also check nested stats object
  const stats = results.stats as Record<string, unknown> | undefined;
  if (stats && typeof stats === "object") {
    if ("min" in stats) lines.push(`Min: ${String(stats.min)}`);
    if ("max" in stats) lines.push(`Max: ${String(stats.max)}`);
    if ("mean" in stats) lines.push(`Mean: ${String(stats.mean)}`);
    if ("std" in stats) lines.push(`Std: ${String(stats.std)}`);
  }

  if (lines.length === 0) {
    // Fallback: stringify top-level keys excluding large base64 fields
    return Object.entries(results)
      .filter(([k]) => k !== "preview_b64" && k !== "processed_b64")
      .map(([k, v]) =>
        `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`,
      )
      .join("\n");
  }

  return lines.join("\n");
}

export default function ExportPanel({
  results,
  processedImageB64,
  isVisible,
}: ExportPanelProps) {
  const [toast, setToast] = useState<ToastState>(null);
  const [saving, setSaving] = useState(false);

  const showToast = useCallback((state: ToastState) => {
    setToast(state);
    setTimeout(() => setToast(null), 3000);
  }, []);

  const hasImage = !!processedImageB64;
  const hasResults = !!results;

  const handleDownloadImage = useCallback(() => {
    if (!processedImageB64) return;
    const byteChars = atob(processedImageB64);
    const byteNumbers = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) {
      byteNumbers[i] = byteChars.charCodeAt(i);
    }
    const blob = new Blob([byteNumbers], { type: "image/png" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "processed_image.png";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [processedImageB64]);

  const handleDownloadStats = useCallback(() => {
    if (!results) return;
    const json = JSON.stringify(results, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "vision_stats.json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [results]);

  const handleCopyStats = useCallback(async () => {
    if (!results) return;
    try {
      const text = extractKeyStats(results);
      await navigator.clipboard.writeText(text);
      showToast({ type: "success", message: "Stats copied to clipboard" });
    } catch {
      showToast({ type: "error", message: "Failed to copy to clipboard" });
    }
  }, [results, showToast]);

  const handleSaveToAssets = useCallback(async () => {
    if (!processedImageB64) return;
    setSaving(true);
    try {
      const res = await fetch("/api/assets/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image: processedImageB64,
          tag: "vision-processing",
        }),
      });
      if (!res.ok) {
        const errorBody = await res.text();
        throw new Error(errorBody || `HTTP ${res.status}`);
      }
      showToast({ type: "success", message: "Saved to assets" });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save to assets";
      showToast({ type: "error", message });
    } finally {
      setSaving(false);
    }
  }, [processedImageB64, showToast]);

  if (!isVisible || (!hasImage && !hasResults)) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h4 className="mb-3 text-sm font-semibold text-gray-700">Export</h4>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleDownloadImage}
          disabled={!hasImage}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <DownloadIcon />
          Download Processed Image
        </button>

        <button
          type="button"
          onClick={handleDownloadStats}
          disabled={!hasResults}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <JsonIcon />
          Download Stats (JSON)
        </button>

        <button
          type="button"
          onClick={handleCopyStats}
          disabled={!hasResults}
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <CopyIcon />
          Copy Stats
        </button>

        <button
          type="button"
          onClick={handleSaveToAssets}
          disabled={!hasImage || saving}
          className="inline-flex items-center gap-1.5 rounded-md border border-blue-300 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SaveIcon />
          {saving ? "Saving\u2026" : "Save to Assets"}
        </button>
      </div>

      {toast && (
        <div
          className={`mt-3 rounded-md px-3 py-2 text-xs font-medium ${
            toast.type === "success"
              ? "bg-green-50 text-green-700"
              : "bg-red-50 text-red-700"
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}
