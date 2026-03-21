"use client";

import React, { useCallback, useEffect, useState } from "react";
import { uploadAsset } from "@/lib/api";
import type { Asset, AssetType } from "@/lib/api";

interface DropUploadZoneProps {
  onUploadComplete: (assets: Asset[]) => void;
}

const EXT_TYPE_MAP: Record<string, AssetType> = {
  jpg: "image",
  jpeg: "image",
  png: "image",
  gif: "image",
  bmp: "image",
  webp: "image",
  svg: "image",
  tiff: "image",
  tif: "image",
  mp4: "video",
  avi: "video",
  mov: "video",
  mkv: "video",
  webm: "video",
  wmv: "video",
  flv: "video",
  wav: "audio",
  mp3: "audio",
  ogg: "audio",
  flac: "audio",
  aac: "audio",
  wma: "audio",
  m4a: "audio",
};

function detectType(filename: string): AssetType {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  return EXT_TYPE_MAP[ext] ?? "image";
}

export interface UploadItem {
  filename: string;
  progress: number;
  status: "uploading" | "done" | "failed";
  error?: string;
}

export default function DropUploadZone({ onUploadComplete }: DropUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [dragCounter, setDragCounter] = useState(0);

  const handleDrop = useCallback(
    async (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      setDragCounter(0);

      const droppedFiles = Array.from(e.dataTransfer?.files ?? []);
      if (droppedFiles.length === 0) return;

      const newUploads: UploadItem[] = droppedFiles.map((f) => ({
        filename: f.name,
        progress: 0,
        status: "uploading" as const,
      }));

      setUploads((prev) => [...prev, ...newUploads]);

      const uploadedAssets: Asset[] = [];

      await Promise.allSettled(
        droppedFiles.map(async (file, idx) => {
          const baseIdx = uploads.length + idx;
          try {
            const asset = await uploadAsset(
              file,
              detectType(file.name),
              [],
              (pct) => {
                setUploads((prev) =>
                  prev.map((u, i) =>
                    i === baseIdx ? { ...u, progress: pct } : u,
                  ),
                );
              },
            );
            setUploads((prev) =>
              prev.map((u, i) =>
                i === baseIdx
                  ? { ...u, progress: 100, status: "done" as const }
                  : u,
              ),
            );
            uploadedAssets.push(asset);
          } catch (err: unknown) {
            const message =
              err instanceof Error ? err.message : "Upload failed";
            setUploads((prev) =>
              prev.map((u, i) =>
                i === baseIdx
                  ? { ...u, status: "failed" as const, error: message }
                  : u,
              ),
            );
          }
        }),
      );

      if (uploadedAssets.length > 0) {
        onUploadComplete(uploadedAssets);
      }
    },
    [onUploadComplete, uploads.length],
  );

  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter((prev) => {
      const next = prev + 1;
      if (next === 1) setIsDragging(true);
      return next;
    });
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter((prev) => {
      const next = prev - 1;
      if (next <= 0) {
        setIsDragging(false);
        return 0;
      }
      return next;
    });
  }, []);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  useEffect(() => {
    document.addEventListener("dragenter", handleDragEnter);
    document.addEventListener("dragleave", handleDragLeave);
    document.addEventListener("dragover", handleDragOver);
    document.addEventListener("drop", handleDrop);

    return () => {
      document.removeEventListener("dragenter", handleDragEnter);
      document.removeEventListener("dragleave", handleDragLeave);
      document.removeEventListener("dragover", handleDragOver);
      document.removeEventListener("drop", handleDrop);
    };
  }, [handleDragEnter, handleDragLeave, handleDragOver, handleDrop]);

  // Auto-clean completed uploads after 5 seconds
  useEffect(() => {
    const doneUploads = uploads.filter((u) => u.status === "done");
    if (doneUploads.length === 0) return;

    const timer = setTimeout(() => {
      setUploads((prev) => prev.filter((u) => u.status !== "done"));
    }, 5000);

    return () => clearTimeout(timer);
  }, [uploads]);

  return (
    <>
      {/* Full-page drag overlay */}
      {isDragging && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-blue-500/10 backdrop-blur-sm">
          <div className="rounded-2xl border-4 border-dashed border-blue-500 bg-white/90 px-16 py-12 shadow-2xl">
            <div className="flex flex-col items-center gap-4">
              <svg
                className="h-16 w-16 text-blue-500"
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
              <p className="text-xl font-semibold text-blue-700">
                Drop files to upload
              </p>
              <p className="text-sm text-blue-500">
                Images, videos, and audio files
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Upload progress toasts */}
      {uploads.length > 0 && (
        <UploadProgressToast uploads={uploads} />
      )}
    </>
  );
}

/* Inline toast component — also exported separately */
function UploadProgressToast({ uploads }: { uploads: UploadItem[] }) {
  if (uploads.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80">
      {uploads.map((upload, idx) => (
        <div
          key={`${upload.filename}-${idx}`}
          className="rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-lg"
        >
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-sm font-medium text-gray-700">
              {upload.filename}
            </p>
            <span
              className={`shrink-0 text-xs font-medium ${
                upload.status === "done"
                  ? "text-green-600"
                  : upload.status === "failed"
                    ? "text-red-600"
                    : "text-blue-600"
              }`}
            >
              {upload.status === "done"
                ? "Done"
                : upload.status === "failed"
                  ? "Failed"
                  : `${upload.progress}%`}
            </span>
          </div>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                upload.status === "done"
                  ? "bg-green-500"
                  : upload.status === "failed"
                    ? "bg-red-500"
                    : "bg-blue-500"
              }`}
              style={{ width: `${upload.progress}%` }}
            />
          </div>
          {upload.status === "failed" && upload.error && (
            <p className="mt-1 text-xs text-red-500">{upload.error}</p>
          )}
        </div>
      ))}
    </div>
  );
}
