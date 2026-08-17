"use client";

import React from "react";
import type { Asset } from "@/lib/api";
import Badge from "@/components/ui/Badge";

interface AssetCardProps {
  asset: Asset;
  selected: boolean;
  onSelect: (id: string) => void;
  onClick: (asset: Asset) => void;
  onPreview?: (asset: Asset) => void;
  onDelete?: (asset: Asset) => void;
}

const typeBadgeVariant: Record<string, "info" | "success" | "warning"> = {
  image: "info",
  video: "success",
  audio: "warning",
};

const indexStatusVariant: Record<string, "success" | "warning" | "neutral"> = {
  indexed: "success",
  pending: "warning",
  failed: "neutral",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function truncateFilename(name: string, max: number = 20): string {
  if (name.length <= max) return name;
  const ext = name.lastIndexOf(".");
  if (ext > 0 && name.length - ext <= 5) {
    const extension = name.slice(ext);
    const stem = name.slice(0, max - extension.length - 1);
    return `${stem}...${extension}`;
  }
  return `${name.slice(0, max - 3)}...`;
}

function TypeIcon({ type }: { type: string }) {
  if (type === "image") {
    return (
      <svg className="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    );
  }
  if (type === "video") {
    return (
      <svg className="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    );
  }
  // audio — waveform icon
  return (
    <svg className="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
  );
}

export default function AssetCard({
  asset,
  selected,
  onSelect,
  onClick,
  onPreview,
  onDelete,
}: AssetCardProps) {
  const indexStatus = asset.index_status;

  return (
    <div
      className={`group relative w-[180px] h-[200px] rounded-lg border bg-white shadow-sm transition-all hover:shadow-md cursor-pointer flex flex-col overflow-hidden ${
        selected ? "border-brand-500 ring-2 ring-brand-200" : "border-gray-200"
      }`}
      onClick={() => onClick(asset)}
    >
      {/* Checkbox — visible on hover or when selected */}
      <div
        className={`absolute top-2 left-2 z-20 transition-opacity ${
          selected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onSelect(asset.id)}
          className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
        />
      </div>

      {/* Index status badge — top-left, offset for checkbox */}
      {indexStatus && (
        <div className="absolute top-2 left-8 z-10">
          <Badge variant={indexStatusVariant[indexStatus] ?? "neutral"} className="text-[10px] px-1.5 py-0.5">
            {indexStatus}
          </Badge>
        </div>
      )}

      {/* Type badge pill — top-right */}
      <div className="absolute top-2 right-2 z-10">
        <Badge variant={typeBadgeVariant[asset.type] ?? "neutral"} className="text-[10px] px-1.5 py-0.5">
          {asset.type}
        </Badge>
      </div>

      {/* Thumbnail area */}
      <div className="relative flex h-[120px] min-h-[120px] items-center justify-center bg-gray-50 overflow-hidden">
        {asset.thumbnail_url ? (
          <img
            src={asset.thumbnail_url}
            alt={asset.filename}
            className="h-full w-full object-cover"
          />
        ) : (
          <TypeIcon type={asset.type} />
        )}

        {/* Hover overlay with action buttons */}
        <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity">
          {onPreview && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onPreview(asset);
              }}
              className="rounded-full bg-white/90 p-2 text-gray-700 hover:bg-white hover:text-brand-600 transition-colors"
              title="Preview"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClick(asset);
            }}
            className="rounded-full bg-white/90 p-2 text-gray-700 hover:bg-white hover:text-brand-600 transition-colors"
            title="Open"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </button>
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(asset);
              }}
              className="rounded-full bg-white/90 p-2 text-gray-700 hover:bg-white hover:text-red-600 transition-colors"
              title="Delete"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="flex-1 p-2 space-y-1">
        <p
          className="text-xs font-medium text-gray-900 truncate"
          title={asset.filename}
        >
          {truncateFilename(asset.filename)}
        </p>
        <div className="flex items-center gap-2 text-[10px] text-gray-500">
          <span>{formatSize(asset.size)}</span>
          <span className="text-gray-300">|</span>
          <span>{formatDate(asset.created_at)}</span>
        </div>
      </div>
    </div>
  );
}

export { formatSize, formatDate, truncateFilename };
