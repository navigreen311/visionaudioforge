"use client";

import React, { useCallback, useRef, useState } from "react";

interface FileUploadProps {
  accept?: string;
  multiple?: boolean;
  onFiles: (files: File[]) => void;
  maxSize?: number; // bytes
}

export default function FileUpload({
  accept,
  multiple = false,
  onFiles,
  maxSize,
}: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return;
      const arr = Array.from(files);
      setError(null);

      if (maxSize) {
        const oversized = arr.find((f) => f.size > maxSize);
        if (oversized) {
          setError(
            `File "${oversized.name}" exceeds max size of ${(maxSize / 1024 / 1024).toFixed(1)}MB`
          );
          return;
        }
      }

      setSelectedFiles(arr);
      onFiles(arr);
    },
    [maxSize, onFiles]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      processFiles(e.dataTransfer.files);
    },
    [processFiles]
  );

  return (
    <div>
      <div
        className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors cursor-pointer ${
          dragOver
            ? "border-brand-500 bg-brand-50"
            : "border-gray-300 bg-gray-50 hover:border-gray-400"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
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
          <span className="font-medium text-brand-600">Click to upload</span> or
          drag and drop
        </p>
        {accept && (
          <p className="mt-1 text-xs text-gray-500">Accepted: {accept}</p>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={(e) => processFiles(e.target.files)}
          className="hidden"
        />
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {selectedFiles.length > 0 && (
        <ul className="mt-3 space-y-1">
          {selectedFiles.map((f, i) => (
            <li
              key={i}
              className="flex items-center gap-2 rounded bg-gray-50 px-3 py-1.5 text-sm text-gray-700"
            >
              <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {f.name}
              <span className="text-xs text-gray-400">
                ({(f.size / 1024).toFixed(1)} KB)
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
