"use client";

import React from "react";
import type { Asset } from "@/lib/api";
import AssetCard from "./AssetCard";

type ViewMode = "grid" | "list";

interface AssetGridProps {
  assets: Asset[];
  viewMode?: ViewMode;
  onAssetClick: (asset: Asset) => void;
  selectedIds: Set<string>;
  onSelectToggle?: (id: string) => void;
  /** @deprecated Use onSelectToggle instead */
  onSelect?: (id: string) => void;
  onUploadClick?: () => void;
  onPreview?: (asset: Asset) => void;
  onDelete?: (asset: Asset) => void;
}

/** Upload icon for empty state */
function UploadIcon() {
  return (
    <svg
      className="h-12 w-12 text-gray-400"
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
  );
}

export default function AssetGrid({
  assets,
  viewMode = "grid",
  onAssetClick,
  selectedIds,
  onSelectToggle,
  onSelect,
  onUploadClick,
  onPreview,
  onDelete,
}: AssetGridProps) {
  const handleSelect = onSelectToggle ?? onSelect;

  if (assets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-white px-6 py-16">
        <UploadIcon />
        <h3 className="mt-4 text-sm font-semibold text-gray-900">No assets yet</h3>
        <p className="mt-1 text-sm text-gray-500">
          Upload your first media asset to get started.
        </p>
        {onUploadClick && (
          <button
            onClick={onUploadClick}
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Upload Asset
          </button>
        )}
      </div>
    );
  }

  if (viewMode === "list") {
    return (
      <div className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white shadow-sm">
        {assets.map((asset) => (
          <div
            key={asset.id}
            className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors"
            onClick={() => onAssetClick(asset)}
          >
            {handleSelect && (
              <div onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={selectedIds.has(asset.id)}
                  onChange={() => handleSelect(asset.id)}
                  className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                />
              </div>
            )}
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-gray-100 overflow-hidden">
              {asset.thumbnail_url ? (
                <img src={asset.thumbnail_url} alt="" className="h-full w-full object-cover" />
              ) : (
                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{asset.filename}</p>
              <p className="text-xs text-gray-500">{asset.type}</p>
            </div>
            <span className="text-xs text-gray-500 shrink-0">
              {new Date(asset.created_at).toLocaleDateString()}
            </span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {assets.map((asset) => (
        <AssetCard
          key={asset.id}
          asset={asset}
          selected={selectedIds.has(asset.id)}
          onSelect={handleSelect ?? (() => {})}
          onClick={onAssetClick}
          onPreview={onPreview}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
