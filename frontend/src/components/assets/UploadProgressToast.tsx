"use client";

import React, { useEffect, useState } from "react";

export interface UploadItem {
  filename: string;
  progress: number;
  status: "uploading" | "done" | "failed";
  error?: string;
}

interface UploadProgressToastProps {
  uploads: UploadItem[];
}

export default function UploadProgressToast({
  uploads,
}: UploadProgressToastProps) {
  const [visible, setVisible] = useState<UploadItem[]>(uploads);

  // Sync incoming uploads and auto-dismiss completed ones after 5s
  useEffect(() => {
    setVisible(uploads);

    const allDone = uploads.every((u) => u.status === "done");
    if (allDone && uploads.length > 0) {
      const timer = setTimeout(() => {
        setVisible([]);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [uploads]);

  if (visible.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80">
      {visible.map((upload, idx) => (
        <div
          key={`${upload.filename}-${idx}`}
          className="animate-in slide-in-from-right rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-lg"
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

          {/* Progress bar */}
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

          {/* Error message */}
          {upload.status === "failed" && upload.error && (
            <p className="mt-1 text-xs text-red-500">{upload.error}</p>
          )}
        </div>
      ))}
    </div>
  );
}
