"use client";

import { API_BASE_URL } from "@/lib/api";

import React, { useCallback, useRef, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type FileStatus = "queued" | "processing" | "done" | "failed";

interface BatchFile {
  id: string;
  file: File;
  status: FileStatus;
  progress: number;
  error?: string;
  resultUrl?: string;
  thumbnail?: string;
}

type BatchOperation =
  | "background-remove"
  | "super-resolution"
  | "style"
  | "auto-crop"
  | "color-grade"
  | "denoise"
  | "silence-remove"
  | "pitch-shift";

interface OperationOption {
  value: BatchOperation;
  label: string;
  type: "video" | "audio";
}

const OPERATIONS: OperationOption[] = [
  { value: "background-remove", label: "Background Remove", type: "video" },
  { value: "super-resolution", label: "Super Resolution", type: "video" },
  { value: "style", label: "Style Transfer", type: "video" },
  { value: "auto-crop", label: "Auto Crop", type: "video" },
  { value: "color-grade", label: "Color Grade", type: "video" },
  { value: "denoise", label: "Denoise Audio", type: "audio" },
  { value: "silence-remove", label: "Remove Silence", type: "audio" },
  { value: "pitch-shift", label: "Pitch Shift", type: "audio" },
];

const STYLE_PRESETS = ["sketch", "edges", "cartoon", "oil_painting"] as const;
const COLOR_PRESETS = ["cinematic", "vintage", "high_contrast", "bw_dramatic"] as const;
const ASPECTS = ["16:9", "4:3", "1:1", "9:16"] as const;

const API_BASE = API_BASE_URL;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isImageFile(file: File): boolean {
  return file.type.startsWith("image/");
}

/* Status badge color map */
const statusConfig: Record<FileStatus, { label: string; bg: string; text: string }> = {
  queued: { label: "Queued", bg: "bg-gray-100", text: "text-gray-700" },
  processing: { label: "Processing", bg: "bg-blue-100", text: "text-blue-800" },
  done: { label: "Done", bg: "bg-green-100", text: "text-green-800" },
  failed: { label: "Failed", bg: "bg-red-100", text: "text-red-800" },
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function BatchTransformTab() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<BatchFile[]>([]);
  const [operation, setOperation] = useState<BatchOperation>("color-grade");
  const [isProcessing, setIsProcessing] = useState(false);

  /* Operation-specific params */
  const [srScale, setSrScale] = useState(2);
  const [stylePreset, setStylePreset] = useState<string>("sketch");
  const [colorPreset, setColorPreset] = useState<string>("cinematic");
  const [aspect, setAspect] = useState<string>("16:9");

  /* ---- Add files ---- */
  const addFiles = useCallback((incoming: FileList | File[]) => {
    const arr = Array.from(incoming);
    const newEntries: BatchFile[] = arr.map((f) => ({
      id: uid(),
      file: f,
      status: "queued" as const,
      progress: 0,
      thumbnail: isImageFile(f) ? URL.createObjectURL(f) : undefined,
    }));
    setFiles((prev) => [...prev, ...newEntries]);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) addFiles(e.target.files);
      e.target.value = "";
    },
    [addFiles],
  );

  /* ---- Build FormData params for chosen operation ---- */
  const buildParams = useCallback((): Record<string, string> => {
    switch (operation) {
      case "super-resolution":
        return { scale: String(srScale) };
      case "style":
        return { style: stylePreset };
      case "color-grade":
        return { preset: colorPreset };
      case "auto-crop":
        return { aspect };
      default:
        return {};
    }
  }, [operation, srScale, stylePreset, colorPreset, aspect]);

  /* ---- Process single file ---- */
  const processOne = useCallback(
    async (bf: BatchFile): Promise<Partial<BatchFile>> => {
      const op = OPERATIONS.find((o) => o.value === operation);
      if (!op) return { status: "failed", error: "Unknown operation" };

      const form = new FormData();
      form.append("file", bf.file);
      const params = buildParams();
      Object.entries(params).forEach(([k, v]) => form.append(k, v));

      const endpoint =
        op.type === "video"
          ? `/api/transform/video/${operation}`
          : `/api/transform/audio/${operation}`;

      const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST", body: form });
      if (!res.ok) throw new Error(`API ${res.status}`);

      const json = await res.json();
      const resultB64 = json.image ?? json.thumbnail ?? json.audio ?? null;
      const resultUrl = resultB64
        ? `data:${op.type === "audio" ? "audio/wav" : "image/png"};base64,${resultB64}`
        : undefined;

      return { status: "done", progress: 100, resultUrl };
    },
    [operation, buildParams],
  );

  /* ---- Process All ---- */
  const processAll = useCallback(async () => {
    setIsProcessing(true);

    const queued = files.filter((f) => f.status === "queued" || f.status === "failed");
    for (const bf of queued) {
      /* Mark processing */
      setFiles((prev) =>
        prev.map((f) => (f.id === bf.id ? { ...f, status: "processing" as const, progress: 30, error: undefined } : f)),
      );

      try {
        const result = await processOne(bf);
        setFiles((prev) =>
          prev.map((f) => (f.id === bf.id ? { ...f, ...result } : f)),
        );
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        setFiles((prev) =>
          prev.map((f) =>
            f.id === bf.id ? { ...f, status: "failed" as const, progress: 0, error: msg } : f,
          ),
        );
      }
    }

    setIsProcessing(false);
  }, [files, processOne]);

  /* ---- Retry single ---- */
  const retryOne = useCallback(
    async (id: string) => {
      const bf = files.find((f) => f.id === id);
      if (!bf) return;

      setFiles((prev) =>
        prev.map((f) => (f.id === id ? { ...f, status: "processing" as const, progress: 30, error: undefined } : f)),
      );

      try {
        const result = await processOne(bf);
        setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, ...result } : f)));
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        setFiles((prev) =>
          prev.map((f) => (f.id === id ? { ...f, status: "failed" as const, progress: 0, error: msg } : f)),
        );
      }
    },
    [files, processOne],
  );

  /* ---- Remove file from queue ---- */
  const removeFile = useCallback((id: string) => {
    setFiles((prev) => {
      const target = prev.find((f) => f.id === id);
      if (target?.thumbnail) URL.revokeObjectURL(target.thumbnail);
      return prev.filter((f) => f.id !== id);
    });
  }, []);

  /* ---- Clear queue ---- */
  const clearQueue = useCallback(() => {
    files.forEach((f) => {
      if (f.thumbnail) URL.revokeObjectURL(f.thumbnail);
    });
    setFiles([]);
  }, [files]);

  /* ---- Download single ---- */
  const downloadOne = useCallback((bf: BatchFile) => {
    if (!bf.resultUrl) return;
    const a = document.createElement("a");
    a.href = bf.resultUrl;
    a.download = `batch-${bf.file.name}`;
    a.click();
  }, []);

  /* ---- Download All as individual files (ZIP placeholder) ---- */
  const downloadAll = useCallback(() => {
    const done = files.filter((f) => f.status === "done" && f.resultUrl);
    done.forEach((bf) => {
      const a = document.createElement("a");
      a.href = bf.resultUrl!;
      a.download = `batch-${bf.file.name}`;
      a.click();
    });
  }, [files]);

  /* ---- Stats ---- */
  const total = files.length;
  const doneCount = files.filter((f) => f.status === "done").length;
  const failedCount = files.filter((f) => f.status === "failed").length;
  const queuedCount = files.filter((f) => f.status === "queued").length;
  const processingCount = files.filter((f) => f.status === "processing").length;
  const allDone = total > 0 && doneCount === total;

  return (
    <div className="space-y-6">
      {/* ---- Upload Zone ---- */}
      <div
        className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-8 transition-colors hover:border-brand-400 cursor-pointer"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <svg
          className="mb-3 h-10 w-10 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
        <p className="text-sm text-gray-600">
          <span className="font-medium text-brand-600">Click to upload</span> or drag &amp; drop
          multiple files
        </p>
        <p className="mt-1 text-xs text-gray-500">Images, audio, or video files</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/*,audio/*,video/*"
          className="hidden"
          onChange={handleInputChange}
        />
      </div>

      {/* ---- Batch Settings ---- */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-900">Batch Settings</h3>
        </div>
        <div className="px-6 py-4 space-y-4">
          {/* Operation dropdown */}
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
            <label className="text-sm font-medium text-gray-700 min-w-[100px]">Operation:</label>
            <select
              value={operation}
              onChange={(e) => setOperation(e.target.value as BatchOperation)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <optgroup label="Video / Image">
                {OPERATIONS.filter((o) => o.type === "video").map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </optgroup>
              <optgroup label="Audio">
                {OPERATIONS.filter((o) => o.type === "audio").map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </optgroup>
            </select>
          </div>

          {/* Operation-specific controls */}
          {operation === "super-resolution" && (
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-gray-700 min-w-[100px]">Scale:</label>
              {[2, 4].map((s) => (
                <button
                  key={s}
                  onClick={() => setSrScale(s)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    srScale === s
                      ? "bg-brand-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {s}x
                </button>
              ))}
            </div>
          )}

          {operation === "style" && (
            <div className="flex flex-wrap items-center gap-2">
              <label className="text-sm font-medium text-gray-700 min-w-[100px]">Style:</label>
              {STYLE_PRESETS.map((s) => (
                <button
                  key={s}
                  onClick={() => setStylePreset(s)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium capitalize transition ${
                    stylePreset === s
                      ? "bg-brand-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {s.replace("_", " ")}
                </button>
              ))}
            </div>
          )}

          {operation === "color-grade" && (
            <div className="flex flex-wrap items-center gap-2">
              <label className="text-sm font-medium text-gray-700 min-w-[100px]">Preset:</label>
              {COLOR_PRESETS.map((p) => (
                <button
                  key={p}
                  onClick={() => setColorPreset(p)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium capitalize transition ${
                    colorPreset === p
                      ? "bg-brand-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  {p.replace("_", " ")}
                </button>
              ))}
            </div>
          )}

          {operation === "auto-crop" && (
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-gray-700 min-w-[100px]">Aspect:</label>
              <select
                value={aspect}
                onChange={(e) => setAspect(e.target.value)}
                className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                {ASPECTS.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="border-t border-gray-200 px-6 py-3 bg-gray-50 rounded-b-lg flex flex-wrap gap-3">
          <button
            onClick={processAll}
            disabled={queuedCount === 0 || isProcessing}
            className="inline-flex items-center gap-2 rounded-lg border border-transparent bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {isProcessing ? "Processing..." : "Process All"}
          </button>
          <button
            onClick={clearQueue}
            disabled={files.length === 0 || isProcessing}
            className="inline-flex items-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Clear Queue
          </button>
          {allDone && doneCount > 1 && (
            <button
              onClick={downloadAll}
              className="inline-flex items-center gap-2 rounded-lg border border-transparent px-4 py-2 text-sm font-medium text-white transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2"
              style={{ backgroundColor: "#0F6E56" }}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download All (ZIP)
            </button>
          )}
        </div>
      </div>

      {/* ---- File List ---- */}
      {files.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="border-b border-gray-200 px-6 py-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Files ({total})
            </h3>
          </div>
          <ul className="divide-y divide-gray-100">
            {files.map((bf) => {
              const sc = statusConfig[bf.status];
              return (
                <li key={bf.id} className="flex items-center gap-4 px-6 py-3">
                  {/* Thumbnail / icon */}
                  <div className="flex-shrink-0 h-10 w-10 rounded bg-gray-100 flex items-center justify-center overflow-hidden">
                    {bf.thumbnail ? (
                      <img
                        src={bf.thumbnail}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
                      </svg>
                    )}
                  </div>

                  {/* File info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{bf.file.name}</p>
                    <p className="text-xs text-gray-500">{formatBytes(bf.file.size)}</p>
                    {/* Progress bar */}
                    {(bf.status === "processing" || bf.status === "done") && (
                      <div className="mt-1 h-1.5 w-full rounded-full bg-gray-200 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${bf.progress}%`,
                            backgroundColor: bf.status === "done" ? "#0F6E56" : "#185FA5",
                          }}
                        />
                      </div>
                    )}
                    {bf.error && (
                      <p className="mt-1 text-xs text-red-600">{bf.error}</p>
                    )}
                  </div>

                  {/* Status badge */}
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${sc.bg} ${sc.text}`}
                  >
                    {sc.label}
                  </span>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {bf.status === "done" && bf.resultUrl && (
                      <button
                        onClick={() => downloadOne(bf)}
                        className="rounded-lg p-1.5 text-green-700 hover:bg-green-50 transition-colors"
                        title="Download"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                      </button>
                    )}
                    {bf.status === "failed" && (
                      <button
                        onClick={() => retryOne(bf.id)}
                        className="rounded-lg p-1.5 text-amber-600 hover:bg-amber-50 transition-colors"
                        title="Retry"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      </button>
                    )}
                    {bf.status !== "processing" && (
                      <button
                        onClick={() => removeFile(bf.id)}
                        className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                        title="Remove"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* ---- Stats Footer ---- */}
      {files.length > 0 && (
        <div className="flex flex-wrap items-center gap-4 rounded-lg bg-gray-50 px-6 py-3 text-sm text-gray-600">
          <span>Total: <strong>{total}</strong></span>
          <span className="text-gray-300">|</span>
          <span>Queued: <strong>{queuedCount}</strong></span>
          <span className="text-gray-300">|</span>
          <span>Processing: <strong>{processingCount}</strong></span>
          <span className="text-gray-300">|</span>
          <span className="text-green-700">Done: <strong>{doneCount}</strong></span>
          <span className="text-gray-300">|</span>
          <span className="text-red-600">Failed: <strong>{failedCount}</strong></span>
        </div>
      )}
    </div>
  );
}
