"use client";

import { useRef } from "react";

export interface Attachment {
  file: File;
  preview: string;
  type: "image" | "audio" | "video";
  base64: string;
}

interface AttachmentInputProps {
  attachment: Attachment | null;
  onAttach: (attachment: Attachment) => void;
  onRemove: () => void;
}

const ACCEPT = "image/*,audio/*,video/*";

function getMediaType(mimeType: string): "image" | "audio" | "video" {
  if (mimeType.startsWith("image/")) return "image";
  if (mimeType.startsWith("audio/")) return "audio";
  return "video";
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Strip the data URL prefix to get raw base64
      const base64 = result.split(",")[1] ?? result;
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function PreviewChip({
  attachment,
  onRemove,
}: {
  attachment: Attachment;
  onRemove: () => void;
}) {
  return (
    <div className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-700">
      {attachment.type === "image" && attachment.preview ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={attachment.preview}
          alt="Preview"
          className="h-6 w-6 rounded object-cover flex-shrink-0"
        />
      ) : attachment.type === "audio" ? (
        <svg
          className="h-4 w-4 text-gray-500 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z"
          />
        </svg>
      ) : (
        <svg
          className="h-4 w-4 text-gray-500 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
          />
        </svg>
      )}
      <span className="truncate max-w-[140px]">{attachment.file.name}</span>
      <button
        type="button"
        onClick={onRemove}
        className="ml-1 text-gray-400 hover:text-gray-600 transition-colors"
        aria-label="Remove attachment"
      >
        &times;
      </button>
    </div>
  );
}

export default function AttachmentInput({
  attachment,
  onAttach,
  onRemove,
}: AttachmentInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const mediaType = getMediaType(file.type);
    const base64 = await fileToBase64(file);
    const preview =
      mediaType === "image" ? URL.createObjectURL(file) : "";

    onAttach({ file, preview, type: mediaType, base64 });

    // Reset input so the same file can be selected again
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      {attachment && (
        <PreviewChip attachment={attachment} onRemove={onRemove} />
      )}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        onChange={handleFileChange}
        className="hidden"
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="inline-flex items-center justify-center w-9 h-9 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        aria-label="Attach file"
        title="Attach image, audio, or video"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
          />
        </svg>
      </button>
    </div>
  );
}
