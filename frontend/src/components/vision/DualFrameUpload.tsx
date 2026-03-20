"use client";

import React from "react";
import ImageUploadPreview from "./ImageUploadPreview";

interface DualFrameUploadProps {
  onFrame1: (file: File) => void;
  onFrame2: (file: File) => void;
}

export default function DualFrameUpload({ onFrame1, onFrame2 }: DualFrameUploadProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <ImageUploadPreview label="Frame 1" onFile={onFrame1} />
      <ImageUploadPreview label="Frame 2" onFile={onFrame2} />
    </div>
  );
}
