"use client";

import React, { useCallback, useState } from "react";

interface AudioExportPanelProps {
  analysisResults: Record<string, unknown> | null;
  spectrogramB64: string | null;
  audioFile: File | null;
}

type FeedbackState = {
  type: "success" | "error";
  message: string;
} | null;

export default function AudioExportPanel({
  analysisResults,
  spectrogramB64,
  audioFile,
}: AudioExportPanelProps) {
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState>(null);

  const downloadJson = useCallback(() => {
    if (!analysisResults) return;
    const blob = new Blob([JSON.stringify(analysisResults, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "audio-features.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [analysisResults]);

  const downloadSpectrogram = useCallback(() => {
    if (!spectrogramB64) return;
    const byteChars = atob(spectrogramB64);
    const byteNumbers = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) {
      byteNumbers[i] = byteChars.charCodeAt(i);
    }
    const blob = new Blob([byteNumbers], { type: "image/png" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "spectrogram.png";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [spectrogramB64]);

  const sendToTraining = useCallback(() => {
    if (!audioFile) return;
    const params = new URLSearchParams({
      source: "audio-analysis",
      filename: audioFile.name,
      hasFeatures: analysisResults ? "true" : "false",
      hasSpectrogram: spectrogramB64 ? "true" : "false",
    });
    window.location.href = `/train?${params.toString()}`;
  }, [audioFile, analysisResults, spectrogramB64]);

  const saveToAssets = useCallback(async () => {
    if (!audioFile) return;
    setSaving(true);
    setFeedback(null);
    try {
      const formData = new FormData();
      formData.append("file", audioFile);
      formData.append("tag", "audio-analysis");
      if (analysisResults) {
        formData.append("metadata", JSON.stringify(analysisResults));
      }
      const res = await fetch("/api/assets", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const errorBody = await res.text();
        throw new Error(errorBody || `HTTP ${res.status}`);
      }
      setFeedback({ type: "success", message: "Saved to assets successfully" });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save asset";
      setFeedback({ type: "error", message });
    } finally {
      setSaving(false);
    }
  }, [audioFile, analysisResults]);

  const btnBase =
    "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors w-full";
  const btnEnabled =
    "bg-gray-100 text-gray-800 hover:bg-gray-200 active:bg-gray-300";
  const btnDisabled = "bg-gray-50 text-gray-400 cursor-not-allowed";

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-700">Export & Actions</h3>

      {/* Download All Features (JSON) */}
      <button
        className={`${btnBase} ${analysisResults ? btnEnabled : btnDisabled}`}
        disabled={!analysisResults}
        onClick={downloadJson}
      >
        <svg
          className="h-4 w-4 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 10v6m0 0l-3-3m3 3l3-3M3 17v2a2 2 0 002 2h14a2 2 0 002-2v-2"
          />
        </svg>
        Download All Features (JSON)
      </button>

      {/* Download Spectrogram (PNG) */}
      <button
        className={`${btnBase} ${spectrogramB64 ? btnEnabled : btnDisabled}`}
        disabled={!spectrogramB64}
        onClick={downloadSpectrogram}
      >
        <svg
          className="h-4 w-4 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        Download Spectrogram (PNG)
      </button>

      {/* Send to Training */}
      <button
        className={`${btnBase} ${audioFile ? btnEnabled : btnDisabled}`}
        disabled={!audioFile}
        onClick={sendToTraining}
      >
        <svg
          className="h-4 w-4 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
        Send to Training
      </button>

      {/* Save to Assets */}
      <button
        className={`${btnBase} ${audioFile && !saving ? btnEnabled : btnDisabled}`}
        disabled={!audioFile || saving}
        onClick={saveToAssets}
      >
        <svg
          className="h-4 w-4 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
          />
        </svg>
        {saving ? "Saving\u2026" : "Save to Assets"}
      </button>

      {/* Feedback banner */}
      {feedback && (
        <div
          className={`rounded-md px-3 py-2 text-sm ${
            feedback.type === "success"
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {feedback.message}
        </div>
      )}
    </div>
  );
}
