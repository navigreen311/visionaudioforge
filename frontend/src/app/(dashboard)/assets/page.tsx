"use client";

import React, { useState, useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listAssets,
  deleteAsset,
  downloadAssetUrl,
} from "@/lib/api";
import type { Asset, AssetFiltersParams } from "@/lib/api";
import AssetFilters, { type AssetFilterValues } from "@/components/assets/AssetFilters";
import AssetGrid from "@/components/assets/AssetGrid";
import AssetUploadModal from "@/components/assets/AssetUploadModal";
import AssetDetailModal from "@/components/assets/AssetDetailModal";
import DataTable, { type Column } from "@/components/ui/DataTable";
import Badge from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { formatSize, formatDate } from "@/components/assets/AssetCard";

type ViewMode = "grid" | "list";

/** Skeleton shimmer card for loading state */
function SkeletonCard() {
  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden animate-pulse">
      <div className="h-40 bg-gray-200" />
      <div className="p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="h-4 w-3/4 rounded bg-gray-200" />
          <div className="h-5 w-12 rounded-full bg-gray-200" />
        </div>
        <div className="flex items-center gap-3">
          <div className="h-3 w-12 rounded bg-gray-200" />
          <div className="h-3 w-16 rounded bg-gray-200" />
        </div>
      </div>
    </div>
  );
}

/** Loading skeleton grid (6 shimmer cards) */
function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

/** Empty state with upload icon */
function EmptyAssetsState({ onUploadClick }: { onUploadClick: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-white px-6 py-16">
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
      <h3 className="mt-4 text-sm font-semibold text-gray-900">No assets yet</h3>
      <p className="mt-1 text-sm text-gray-500">
        Upload your first media asset to get started.
      </p>
      <button
        onClick={onUploadClick}
        className="mt-4 inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 transition-colors"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        Upload Asset
      </button>
    </div>
  );
}

export default function AssetsPage() {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  // View & filter state
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [filters, setFilters] = useState<AssetFilterValues>({
    type: "",
    tags: "",
    search: "",
    sort_by: "created_at",
    sort_dir: "desc",
  });
  const [page, setPage] = useState(1);
  const pageSize = 24;

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Modal state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [detailAsset, setDetailAsset] = useState<Asset | null>(null);

  // Build API params
  const apiParams = useMemo<AssetFiltersParams>(() => {
    const params: AssetFiltersParams = {
      sort_by: filters.sort_by,
      sort_dir: filters.sort_dir,
      page,
      page_size: pageSize,
    };
    if (filters.type) params.type = filters.type as AssetFiltersParams["type"];
    if (filters.tags) params.tags = filters.tags;
    if (filters.search) params.search = filters.search;
    return params;
  }, [filters, page]);

  // Fetch assets with AbortController timeout
  const { data, isLoading, error } = useQuery({
    queryKey: ["assets", apiParams],
    queryFn: async ({ signal }) => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10_000);

      // Forward react-query's signal abort to our controller
      signal?.addEventListener("abort", () => controller.abort());

      try {
        const result = await listAssets(apiParams);
        return result;
      } finally {
        clearTimeout(timeout);
      }
    },
    retry: 1,
  });

  // Guard API response: ensure items is always an array
  const rawData = data as Record<string, unknown> | undefined;
  const assets: Asset[] = Array.isArray(rawData)
    ? rawData
    : Array.isArray(rawData?.items)
      ? (rawData.items as Asset[])
      : [];
  const total = typeof rawData?.total === "number" ? rawData.total : 0;

  // Selection handlers
  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleFilterChange = useCallback((newFilters: AssetFilterValues) => {
    setFilters(newFilters);
    setPage(1);
    setSelectedIds(new Set());
  }, []);

  const refreshAssets = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["assets"] });
    setSelectedIds(new Set());
  }, [queryClient]);

  // Bulk actions
  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} asset(s)? This cannot be undone.`)) return;

    try {
      await Promise.all(Array.from(selectedIds).map((id) => deleteAsset(id)));
      addToast("success", `Deleted ${selectedIds.size} asset(s).`);
      refreshAssets();
    } catch {
      addToast("error", "Some assets could not be deleted.");
    }
  }, [selectedIds, addToast, refreshAssets]);

  const handleBulkDownload = useCallback(() => {
    selectedIds.forEach((id) => {
      window.open(downloadAssetUrl(id), "_blank");
    });
  }, [selectedIds]);

  // List view columns
  const columns = useMemo<Column<Asset & Record<string, unknown>>[]>(
    () => [
      {
        key: "thumbnail_url",
        label: "Preview",
        render: (_val: unknown, row: Asset) =>
          row.thumbnail_url ? (
            <img
              src={row.thumbnail_url}
              alt=""
              className="h-10 w-10 rounded object-cover"
            />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded bg-gray-100 text-gray-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          ),
      },
      {
        key: "filename",
        label: "Filename",
        sortable: true,
        render: (_val: unknown, row: Asset) => (
          <button
            onClick={() => setDetailAsset(row)}
            className="text-brand-600 hover:text-brand-700 hover:underline font-medium text-left"
          >
            {row.filename}
          </button>
        ),
      },
      {
        key: "type",
        label: "Type",
        sortable: true,
        render: (_val: unknown, row: Asset) => {
          const v: Record<string, "info" | "success" | "warning"> = {
            image: "info",
            video: "success",
            audio: "warning",
          };
          return <Badge variant={v[row.type] ?? "neutral"}>{row.type}</Badge>;
        },
      },
      {
        key: "size",
        label: "Size",
        sortable: true,
        render: (_val: unknown, row: Asset) => formatSize(row.size),
      },
      {
        key: "tags",
        label: "Tags",
        render: (_val: unknown, row: Asset) => (
          <div className="flex flex-wrap gap-1 max-w-[200px]">
            {row.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
              >
                {tag}
              </span>
            ))}
            {row.tags.length > 3 && (
              <span className="text-xs text-gray-400">+{row.tags.length - 3}</span>
            )}
          </div>
        ),
      },
      {
        key: "created_at",
        label: "Created",
        sortable: true,
        render: (_val: unknown, row: Asset) => formatDate(row.created_at),
      },
      {
        key: "actions",
        label: "Actions",
        render: (_val: unknown, row: Asset) => (
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                window.open(downloadAssetUrl(row.id), "_blank");
              }}
              className="rounded p-1 text-gray-400 hover:text-brand-600 hover:bg-gray-100 transition-colors"
              title="Download"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </button>
            <button
              onClick={async (e) => {
                e.stopPropagation();
                if (!confirm(`Delete "${row.filename}"?`)) return;
                try {
                  await deleteAsset(row.id);
                  addToast("success", `Deleted "${row.filename}".`);
                  refreshAssets();
                } catch {
                  addToast("error", "Failed to delete asset.");
                }
              }}
              className="rounded p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
              title="Delete"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ),
      },
    ],
    [addToast, refreshAssets],
  );

  const handleSort = useCallback(
    (key: string, direction: "asc" | "desc") => {
      const sortMap: Record<string, AssetFilterValues["sort_by"]> = {
        filename: "filename",
        size: "size",
        created_at: "created_at",
      };
      const sortBy = sortMap[key];
      if (sortBy) {
        setFilters((prev) => ({ ...prev, sort_by: sortBy, sort_dir: direction }));
        setPage(1);
      }
    },
    [],
  );

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Media Asset Library</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage images, videos, and audio files for your AI workflows.
        </p>
      </div>

      {/* Toolbar / Filters */}
      <AssetFilters
        filters={filters}
        onChange={handleFilterChange}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onUploadClick={() => setUploadOpen(true)}
        selectedCount={selectedIds.size}
        onBulkDelete={handleBulkDelete}
        onBulkDownload={handleBulkDownload}
      />

      {/* Content area */}
      {isLoading ? (
        <SkeletonGrid />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-6 py-8 text-center">
          <p className="text-sm text-red-600">
            Failed to load assets. Please try again.
          </p>
          <button
            onClick={refreshAssets}
            className="mt-3 inline-flex items-center rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 transition-colors"
          >
            Retry
          </button>
        </div>
      ) : assets.length === 0 ? (
        <EmptyAssetsState onUploadClick={() => setUploadOpen(true)} />
      ) : viewMode === "grid" ? (
        <AssetGrid
          assets={assets}
          selectedIds={selectedIds}
          onSelect={toggleSelect}
          onAssetClick={setDetailAsset}
          onUploadClick={() => setUploadOpen(true)}
        />
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
          <DataTable
            columns={columns}
            data={assets as (Asset & Record<string, unknown>)[]}
            onSort={handleSort}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: setPage,
            }}
          />
        </div>
      )}

      {/* Pagination for grid view */}
      {viewMode === "grid" && !isLoading && !error && total > pageSize && (
        <div className="flex items-center justify-between border-t border-gray-200 pt-4">
          <span className="text-sm text-gray-700">
            Page {page} of {Math.ceil(total / pageSize)}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50 hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= Math.ceil(total / pageSize)}
              className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      <AssetUploadModal
        isOpen={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploadComplete={refreshAssets}
      />

      {/* Detail Modal */}
      <AssetDetailModal
        asset={detailAsset}
        onClose={() => setDetailAsset(null)}
        onDeleted={refreshAssets}
        onUpdated={refreshAssets}
      />
    </div>
  );
}
