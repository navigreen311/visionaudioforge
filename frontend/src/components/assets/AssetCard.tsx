"use client";

import React from "react";
import type { Asset } from "@/lib/api";
import Badge from "@/components/ui/Badge";

interface AssetCardProps {
  asset: Asset;
  selected: boolean;
  onSelect: (id: string) => void;
  onClick: (asset: Asset) => void;
}

const typeBadgeVariant: Record<string, "info" | "success" | "warning"> = {
  image: "info",
  video: "success",
  audio: "warning",
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
  // audio
  return (
    <svg className="h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
    </svg>
  );
}

export default function AssetCard({ asset, selected, onSelect, onClick }: AssetCardProps) {
  return (
    <div
      className={`group relative rounded-lg border bg-white shadow-sm transition-all hover:shadow-md cursor-pointer ${
        selected ? "border-brand-500 ring-2 ring-brand-200" : "border-gray-200"
      }`}
      onClick={() => onClick(asset)}
    >
      {/* Checkbox */}
      <div
        className="absolute top-2 left-2 z-10"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onSelect(asset.id)}
          className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
        />
      </div>

      {/* Thumbnail area */}
      <div className="flex h-40 items-center justify-center rounded-t-lg bg-gray-50 overflow-hidden">
        {asset.thumbnail_url ? (
          <img
            src={asset.thumbnail_url}
            alt={asset.filename}
            className="h-full w-full object-cover"
          />
        ) : (
          <TypeIcon type={asset.type} />
        )}
      </div>

      {/* Info */}
      <div className="p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium text-gray-900 truncate flex-1" title={asset.filename}>
            {asset.filename}
          </p>
          <Badge variant={typeBadgeVariant[asset.type] ?? "neutral"}>
            {asset.type}
          </Badge>
        </div>

        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>{formatSize(asset.size)}</span>
          <span>{formatDate(asset.created_at)}</span>
        </div>

        {asset.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {asset.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
              >
                {tag}
              </span>
            ))}
            {asset.tags.length > 4 && (
              <span className="text-xs text-gray-400">+{asset.tags.length - 4}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export { formatSize, formatDate };
