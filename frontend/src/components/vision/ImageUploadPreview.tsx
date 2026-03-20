"use client";

import React, { useState, useCallback } from "react";
import FileUpload from "@/components/ui/FileUpload";

interface ImageUploadPreviewProps {
  label?: string;
  onFile: (file: File) => void;
  accept?: string;
}

export default function ImageUploadPreview({
  label,
  onFile,
  accept = "image/*",
}: ImageUploadPreviewProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState<{ w: number; h: number } | null>(null);

  const handleFiles = useCallback(
    (files: File[]) => {
      if (files.length === 0) return;
      const file = files[0];
      onFile(file);

      const url = URL.createObjectURL(file);
      setPreview(url);

      const img = new Image();
      img.onload = () => {
        setDimensions({ w: img.naturalWidth, h: img.naturalHeight });
        URL.revokeObjectURL(url);
      };
      img.src = url;
    },
    [onFile],
  );

  return (
    <div>
      {label && (
        <label className="mb-2 block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <FileUpload accept={accept} onFiles={handleFiles} maxSize={20 * 1024 * 1024} />
      {preview && (
        <div className="mt-3">
          <img
            src={preview}
            alt="Preview"
            className="max-h-64 rounded border border-gray-200 object-contain"
          />
          {dimensions && (
            <p className="mt-1 text-xs text-gray-500">
              {dimensions.w} x {dimensions.h} px
            </p>
          )}
        </div>
      )}
    </div>
  );
}
