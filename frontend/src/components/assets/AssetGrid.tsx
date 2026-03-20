"use client";

import React from "react";
import type { Asset } from "@/lib/api";
import AssetCard from "./AssetCard";
import EmptyState from "@/components/ui/EmptyState";

interface AssetGridProps {
  assets: Asset[];
  selectedIds: Set<string>;
  onSelect: (id: string) => void;
  onAssetClick: (asset: Asset) => void;
  onUploadClick: () => void;
}

export default function AssetGrid({
  assets,
  selectedIds,
  onSelect,
  onAssetClick,
  onUploadClick,
}: AssetGridProps) {
  if (assets.length === 0) {
    return (
      <EmptyState
        icon={
          <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        }
        title="No assets found"
        description="Upload your first media asset to get started."
        action={{ label: "Upload Asset", onClick: onUploadClick }}
      />
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {assets.map((asset) => (
        <AssetCard
          key={asset.id}
          asset={asset}
          selected={selectedIds.has(asset.id)}
          onSelect={onSelect}
          onClick={onAssetClick}
        />
      ))}
    </div>
  );
}
