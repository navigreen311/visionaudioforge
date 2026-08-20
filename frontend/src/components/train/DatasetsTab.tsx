"use client";

import { readWorkspaceId } from "@/lib/session";

import React, { useState, useEffect, useCallback } from "react";
import api, { API_BASE_URL } from "@/lib/api";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import Modal from "@/components/ui/Modal";
import FileUpload from "@/components/ui/FileUpload";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import DatasetDetailPanel from "./DatasetDetailPanel";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DatasetSplit {
  train: number;
  val: number;
  test: number;
}

interface DatasetRecord {
  id: string;
  name: string;
  modality: string;
  sample_count: number;
  version: number;
  split: DatasetSplit;
  class_counts: Record<string, number>;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

interface PaginatedDatasets {
  items: DatasetRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

type Modality = "image" | "audio" | "video" | "multimodal";

const MODALITY_OPTIONS: { value: Modality; label: string }[] = [
  { value: "image", label: "Image" },
  { value: "audio", label: "Audio" },
  { value: "video", label: "Video" },
  { value: "multimodal", label: "Multimodal" },
];

const MODALITY_BADGE_VARIANT: Record<string, string> = {
  image: "info",
  audio: "success",
  video: "warning",
  multimodal: "neutral",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Was a local reimplementation that fell back to the nil workspace when
// there was no session, so an unauthenticated render asked for somebody
// else's tenant. `readWorkspaceId` reads the signed claim first and returns
// null rather than inventing one.
function getWorkspaceId(): string {
  return readWorkspaceId() ?? "";
}

function isHealthy(classCounts: Record<string, number>): boolean {
  const counts = Object.values(classCounts);
  if (counts.length < 2) return true;
  const min = Math.min(...counts);
  const max = Math.max(...counts);
  return min > 0 && max / min <= 5;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ---------------------------------------------------------------------------
// SplitBar: mini 3-color progress bar
// ---------------------------------------------------------------------------

function SplitBar({ split }: { split: DatasetSplit }) {
  const total = split.train + split.val + split.test;
  if (total === 0) {
    return <div className="h-2.5 w-24 rounded-full bg-gray-100" />;
  }
  const trainW = (split.train / total) * 100;
  const valW = (split.val / total) * 100;
  const testW = (split.test / total) * 100;

  return (
    <div className="flex items-center gap-2">
      <div className="flex h-2.5 w-24 overflow-hidden rounded-full bg-gray-100">
        <div className="bg-blue-500" style={{ width: `${trainW}%` }} />
        <div className="bg-amber-400" style={{ width: `${valW}%` }} />
        <div className="bg-green-500" style={{ width: `${testW}%` }} />
      </div>
      <span className="text-xs text-gray-400 whitespace-nowrap">
        {split.train}/{split.val}/{split.test}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// HealthBadge
// ---------------------------------------------------------------------------

function HealthBadge({ classCounts }: { classCounts: Record<string, number> }) {
  const healthy = isHealthy(classCounts);
  return healthy ? (
    <span className="inline-flex items-center gap-1 text-green-600" title="Balanced">
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
      <span className="text-xs">OK</span>
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-amber-500" title="Imbalanced (>5:1 ratio)">
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
        />
      </svg>
      <span className="text-xs">Warn</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Upload Modal
// ---------------------------------------------------------------------------

interface UploadForm {
  name: string;
  version: string;
  modality: Modality;
  trainPct: number;
  valPct: number;
  testPct: number;
  file: File | null;
}

function UploadDatasetModal({
  isOpen,
  onClose,
  onUploaded,
}: {
  isOpen: boolean;
  onClose: () => void;
  onUploaded: () => void;
}) {
  const [form, setForm] = useState<UploadForm>({
    name: "",
    version: "1.0",
    modality: "image",
    trainPct: 70,
    valPct: 15,
    testPct: 15,
    file: null,
  });
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTrainChange = useCallback((v: number) => {
    const clamped = Math.min(Math.max(v, 0), 100);
    const remaining = 100 - clamped;
    setForm((prev) => ({
      ...prev,
      trainPct: clamped,
      valPct: Math.round(remaining / 2),
      testPct: remaining - Math.round(remaining / 2),
    }));
  }, []);

  const handleValChange = useCallback(
    (v: number) => {
      const maxVal = 100 - form.trainPct;
      const clamped = Math.min(Math.max(v, 0), maxVal);
      setForm((prev) => ({
        ...prev,
        valPct: clamped,
        testPct: maxVal - clamped,
      }));
    },
    [form.trainPct]
  );

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      setError("Dataset name is required.");
      return;
    }
    setError(null);
    setUploading(true);

    try {
      // 1. Create dataset
      const { data: created } = await api.post("/api/datasets", {
        name: form.name,
        modality: form.modality,
        workspace_id: getWorkspaceId(),
      });

      // 2. Upload file if provided
      if (form.file) {
        const fd = new FormData();
        fd.append("files", form.file);
        await api.post(`/api/datasets/${created.id}/upload`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      // 3. Split
      await api.post(`/api/datasets/${created.id}/split`, {
        train: form.trainPct / 100,
        val: form.valPct / 100,
        test: form.testPct / 100,
        stratified: true,
      });

      onUploaded();
      onClose();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Upload failed. Please try again.";
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  const sumValid = form.trainPct + form.valPct + form.testPct === 100;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Upload Dataset"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={uploading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={uploading} disabled={!sumValid}>
            Upload &amp; Index
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && (
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Dataset Name
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            placeholder="e.g. COCO-2024-subset"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none"
          />
        </div>

        {/* Version */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Version
          </label>
          <input
            type="text"
            value={form.version}
            onChange={(e) => setForm((prev) => ({ ...prev, version: e.target.value }))}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none"
          />
        </div>

        {/* Modality */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Modality
          </label>
          <select
            value={form.modality}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, modality: e.target.value as Modality }))
            }
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none bg-white"
          >
            {MODALITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* File Dropzone */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            File
          </label>
          <FileUpload
            accept=".zip,.tar.gz,.tgz"
            onFiles={(files) =>
              setForm((prev) => ({ ...prev, file: files[0] ?? null }))
            }
            maxSize={5 * 1024 * 1024 * 1024} // 5GB
          />
        </div>

        {/* Split Sliders */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Train / Val / Test Split
          </label>
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-0.5">
              <span>Train</span>
              <span>{form.trainPct}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={form.trainPct}
              onChange={(e) => handleTrainChange(Number(e.target.value))}
              className="w-full accent-blue-500"
            />
          </div>
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-0.5">
              <span>Val</span>
              <span>{form.valPct}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100 - form.trainPct}
              value={form.valPct}
              onChange={(e) => handleValChange(Number(e.target.value))}
              className="w-full accent-amber-400"
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>Test</span>
            <span>{form.testPct}%</span>
          </div>
          {!sumValid && (
            <p className="text-xs text-red-500">Split percentages must sum to 100%.</p>
          )}
        </div>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// DatasetsTab (main export)
// ---------------------------------------------------------------------------

export default function DatasetsTab() {
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showUpload, setShowUpload] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<DatasetRecord | null>(null);

  const PAGE_SIZE = 20;

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * PAGE_SIZE;
      const { data } = await api.get<PaginatedDatasets>("/api/datasets", {
        params: { workspace_id: getWorkspaceId(), skip, limit: PAGE_SIZE },
      });
      setDatasets(data.items);
      setTotalPages(data.total_pages);
    } catch {
      // Gracefully handle -- show empty
      setDatasets([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleResplit = async (id: string, train: number, val: number, test: number) => {
    try {
      await api.post(`/api/datasets/${id}/split`, { train, val, test, stratified: true });
      fetchDatasets();
    } catch {
      // Silently fail -- could add toast
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this dataset?")) return;
    try {
      await api.delete(`/api/datasets/${id}`);
      fetchDatasets();
    } catch {
      // Silently fail
    }
  };

  const handleExport = (id: string) => {
    const base = API_BASE_URL;
    window.open(`${base}/api/datasets/${id}/export?format=json`, "_blank");
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Datasets</h2>
          <p className="text-sm text-gray-500">
            Manage training datasets, splits, and class distributions.
          </p>
        </div>
        <Button onClick={() => setShowUpload(true)}>
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Upload Dataset
        </Button>
      </div>

      {/* Table or empty state */}
      {datasets.length === 0 ? (
        <EmptyState
          icon={
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
              />
            </svg>
          }
          title="No datasets yet"
          description="Upload your first dataset to start training models."
          action={{ label: "Upload Dataset", onClick: () => setShowUpload(true) }}
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {["Name", "Modality", "Samples", "Version", "Split", "Health", "Actions"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {datasets.map((ds) => (
                  <tr key={ds.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                      {ds.name}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Badge variant={MODALITY_BADGE_VARIANT[ds.modality] ?? "neutral"}>
                        {capitalize(ds.modality)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">
                      {ds.sample_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700 whitespace-nowrap">
                      v{ds.version}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <SplitBar split={ds.split} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <HealthBadge classCounts={ds.class_counts} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setSelectedDataset(ds)}
                          className="rounded px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 transition-colors"
                          title="View details"
                        >
                          View
                        </button>
                        <button
                          onClick={() => setSelectedDataset(ds)}
                          className="rounded px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 transition-colors"
                          title="Re-split dataset"
                        >
                          Re-split
                        </button>
                        <button
                          onClick={() => handleExport(ds.id)}
                          className="rounded px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 transition-colors"
                          title="Download dataset"
                        >
                          Download
                        </button>
                        <button
                          onClick={() => handleDelete(ds.id)}
                          className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
                          title="Delete dataset"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">
                Page {page} of {totalPages}
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
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50 hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Upload Modal */}
      <UploadDatasetModal
        isOpen={showUpload}
        onClose={() => setShowUpload(false)}
        onUploaded={fetchDatasets}
      />

      {/* Detail Panel */}
      {selectedDataset && (
        <DatasetDetailPanel
          dataset={selectedDataset}
          isOpen={!!selectedDataset}
          onClose={() => setSelectedDataset(null)}
          onResplit={handleResplit}
        />
      )}
    </div>
  );
}
