"use client";

import React, { useCallback, useState } from "react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import FileUpload from "@/components/ui/FileUpload";
import { uploadAsset } from "@/lib/api";
import type { AssetType } from "@/lib/api";

interface AssetUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete: () => void;
}

interface FileEntry {
  file: File;
  type: AssetType;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
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

export default function AssetUploadModal({
  isOpen,
  onClose,
  onUploadComplete,
}: AssetUploadModalProps) {
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [tags, setTags] = useState("");
  const [uploading, setUploading] = useState(false);

  const handleFiles = useCallback((newFiles: File[]) => {
    setFiles((prev) => [
      ...prev,
      ...newFiles.map((file) => ({
        file,
        type: detectType(file.name),
        progress: 0,
        status: "pending" as const,
      })),
    ]);
  }, []);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadAll = async () => {
    if (files.length === 0) return;
    setUploading(true);
    const tagList = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    let hasError = false;

    for (let i = 0; i < files.length; i++) {
      if (files[i].status === "done") continue;

      setFiles((prev) =>
        prev.map((f, idx) =>
          idx === i ? { ...f, status: "uploading" as const, progress: 0 } : f,
        ),
      );

      try {
        await uploadAsset(files[i].file, files[i].type, tagList, (pct) => {
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, progress: pct } : f,
            ),
          );
        });
        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i ? { ...f, status: "done" as const, progress: 100 } : f,
          ),
        );
      } catch (err: unknown) {
        hasError = true;
        const message = err instanceof Error ? err.message : "Upload failed";
        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i ? { ...f, status: "error" as const, error: message } : f,
          ),
        );
      }
    }

    setUploading(false);
    if (!hasError) {
      onUploadComplete();
      handleClose();
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setFiles([]);
      setTags("");
      onClose();
    }
  };

  const allDone = files.length > 0 && files.every((f) => f.status === "done");
  const pendingCount = files.filter((f) => f.status === "pending" || f.status === "error").length;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Upload Assets"
      footer={
        <div className="flex gap-3">
          <Button variant="secondary" onClick={handleClose} disabled={uploading}>
            {allDone ? "Close" : "Cancel"}
          </Button>
          {!allDone && (
            <Button
              onClick={handleUploadAll}
              loading={uploading}
              disabled={files.length === 0}
            >
              Upload {pendingCount > 0 ? `(${pendingCount})` : ""}
            </Button>
          )}
        </div>
      }
    >
      <div className="space-y-4">
        {/* Drop zone */}
        <FileUpload
          accept="image/*,video/*,audio/*"
          multiple
          onFiles={handleFiles}
          maxSize={500 * 1024 * 1024}
        />

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Tags (comma-separated, optional)
          </label>
          <input
            type="text"
            placeholder="e.g. evidence, scene1, night"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* File list with progress */}
        {files.length > 0 && (
          <div className="max-h-60 overflow-y-auto space-y-2">
            {files.map((entry, i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2"
              >
                {/* Type indicator */}
                <span
                  className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                    entry.type === "image"
                      ? "bg-blue-100 text-blue-700"
                      : entry.type === "video"
                        ? "bg-green-100 text-green-700"
                        : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {entry.type}
                </span>

                {/* File info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-700 truncate">{entry.file.name}</p>
                  {/* Progress bar */}
                  {(entry.status === "uploading" || entry.status === "done") && (
                    <div className="mt-1 h-1.5 w-full rounded-full bg-gray-200">
                      <div
                        className={`h-1.5 rounded-full transition-all ${
                          entry.status === "done" ? "bg-green-500" : "bg-brand-600"
                        }`}
                        style={{ width: `${entry.progress}%` }}
                      />
                    </div>
                  )}
                  {entry.status === "error" && (
                    <p className="mt-0.5 text-xs text-red-600">{entry.error}</p>
                  )}
                </div>

                {/* Status / remove */}
                {entry.status === "done" ? (
                  <svg className="h-5 w-5 text-green-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : entry.status !== "uploading" ? (
                  <button
                    onClick={() => removeFile(i)}
                    className="text-gray-400 hover:text-red-500 transition-colors shrink-0"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                ) : (
                  <span className="text-xs text-gray-500 shrink-0">{entry.progress}%</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}
