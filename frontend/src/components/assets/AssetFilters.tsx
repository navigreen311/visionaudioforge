"use client";

import React from "react";
import type { AssetType } from "@/lib/api";

export interface AssetFilterValues {
  type: AssetType | "";
  tags: string;
  search: string;
  sort_by: "created_at" | "filename" | "size";
  sort_dir: "asc" | "desc";
}

type ViewMode = "grid" | "list";

interface AssetFiltersProps {
  filters: AssetFilterValues;
  onChange: (filters: AssetFilterValues) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  onUploadClick: () => void;
  selectedCount: number;
  onBulkDelete?: () => void;
  onBulkDownload?: () => void;
}

export default function AssetFilters({
  filters,
  onChange,
  viewMode,
  onViewModeChange,
  onUploadClick,
  selectedCount,
  onBulkDelete,
  onBulkDownload,
}: AssetFiltersProps) {
  const update = (patch: Partial<AssetFilterValues>) => {
    onChange({ ...filters, ...patch });
  };

  return (
    <div className="space-y-3">
      {/* Top toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* View toggle */}
        <div className="flex rounded-lg border border-gray-300 overflow-hidden">
          <button
            onClick={() => onViewModeChange("grid")}
            className={`px-3 py-2 text-sm font-medium transition-colors ${
              viewMode === "grid"
                ? "bg-brand-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-50"
            }`}
            title="Grid view"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
          </button>
          <button
            onClick={() => onViewModeChange("list")}
            className={`px-3 py-2 text-sm font-medium transition-colors ${
              viewMode === "list"
                ? "bg-brand-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-50"
            }`}
            title="List view"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        {/* Type filter */}
        <select
          value={filters.type}
          onChange={(e) => update({ type: e.target.value as AssetType | "" })}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        >
          <option value="">All Types</option>
          <option value="image">Image</option>
          <option value="video">Video</option>
          <option value="audio">Audio</option>
        </select>

        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search assets..."
            value={filters.search}
            onChange={(e) => update({ search: e.target.value })}
            className="w-full rounded-lg border border-gray-300 bg-white pl-10 pr-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* Tags input */}
        <input
          type="text"
          placeholder="Filter by tags..."
          value={filters.tags}
          onChange={(e) => update({ tags: e.target.value })}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 w-48"
        />

        {/* Sort */}
        <select
          value={`${filters.sort_by}:${filters.sort_dir}`}
          onChange={(e) => {
            const [sort_by, sort_dir] = e.target.value.split(":") as [
              AssetFilterValues["sort_by"],
              AssetFilterValues["sort_dir"],
            ];
            update({ sort_by, sort_dir });
          }}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        >
          <option value="created_at:desc">Newest First</option>
          <option value="created_at:asc">Oldest First</option>
          <option value="filename:asc">Name A-Z</option>
          <option value="filename:desc">Name Z-A</option>
          <option value="size:desc">Largest</option>
          <option value="size:asc">Smallest</option>
        </select>

        {/* Upload button */}
        <button
          onClick={onUploadClick}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Upload
        </button>
      </div>

      {/* Bulk actions bar */}
      {selectedCount > 0 && (
        <div className="flex items-center gap-3 rounded-lg bg-brand-50 border border-brand-200 px-4 py-2">
          <span className="text-sm font-medium text-brand-700">
            {selectedCount} asset{selectedCount !== 1 ? "s" : ""} selected
          </span>
          <button
            onClick={onBulkDownload}
            className="inline-flex items-center gap-1 rounded px-3 py-1 text-sm font-medium text-brand-700 hover:bg-brand-100 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download
          </button>
          <button
            onClick={onBulkDelete}
            className="inline-flex items-center gap-1 rounded px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-100 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete
          </button>
        </div>
      )}
    </div>
  );
}
