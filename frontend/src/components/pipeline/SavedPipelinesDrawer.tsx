"use client";

import { useCallback, useEffect, useState } from "react";

import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type PipelineStatus = "Draft" | "Active" | "Scheduled";

interface SavedPipeline {
  id: string;
  name: string;
  description?: string;
  node_count: number;
  status: PipelineStatus;
  updated_at: string;
  definition: {
    nodes: Array<Record<string, unknown>>;
    edges: Array<Record<string, unknown>>;
  };
}

interface SavedPipelinesDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onLoad: (pipeline: SavedPipeline) => void;
  hasUnsavedChanges?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_BADGE: Record<PipelineStatus, string> = {
  Draft: "bg-gray-100 text-gray-600",
  Active: "bg-green-100 text-green-700",
  Scheduled: "bg-blue-100 text-blue-700",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function deriveStatus(pipeline: {
  updated_at: string;
  definition: { nodes: Array<Record<string, unknown>> };
}): PipelineStatus {
  if (pipeline.definition.nodes.length === 0) return "Draft";
  return "Active";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SavedPipelinesDrawer({
  isOpen,
  onClose,
  onLoad,
  hasUnsavedChanges = false,
}: SavedPipelinesDrawerProps) {
  const [pipelines, setPipelines] = useState<SavedPipeline[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    type: "load" | "delete";
    pipeline: SavedPipeline;
  } | null>(null);

  const fetchPipelines = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get("/api/pipeline/list");
      const items: SavedPipeline[] = (data.items ?? data).map(
        (p: Record<string, unknown>) => ({
          id: p.id as string,
          name: (p.name as string) || "Untitled",
          description: p.description as string | undefined,
          node_count: Array.isArray(
            (p.definition as Record<string, unknown>)?.nodes
          )
            ? (
                (p.definition as Record<string, unknown>)
                  ?.nodes as Array<unknown>
              ).length
            : 0,
          status: deriveStatus({
            updated_at: p.updated_at as string,
            definition: (p.definition as {
              nodes: Array<Record<string, unknown>>;
            }) ?? { nodes: [] },
          }),
          updated_at: p.updated_at as string,
          definition: (p.definition as SavedPipeline["definition"]) ?? {
            nodes: [],
            edges: [],
          },
        })
      );
      setPipelines(items);
    } catch {
      setError("Failed to load pipelines");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchPipelines();
    }
  }, [isOpen, fetchPipelines]);

  const handleLoad = (pipeline: SavedPipeline) => {
    if (hasUnsavedChanges) {
      setConfirmAction({ type: "load", pipeline });
    } else {
      onLoad(pipeline);
    }
  };

  const handleDuplicate = async (pipeline: SavedPipeline) => {
    try {
      await api.post("/api/pipeline/save", {
        name: `${pipeline.name} (copy)`,
        definition: pipeline.definition,
        workspace_id: "00000000-0000-0000-0000-000000000000",
      });
      await fetchPipelines();
    } catch {
      setError("Duplicate failed");
    }
  };

  const handleDelete = (pipeline: SavedPipeline) => {
    setConfirmAction({ type: "delete", pipeline });
  };

  const confirmActionHandler = async () => {
    if (!confirmAction) return;
    if (confirmAction.type === "load") {
      onLoad(confirmAction.pipeline);
    } else if (confirmAction.type === "delete") {
      try {
        await api.delete(`/api/pipeline/${confirmAction.pipeline.id}`);
        await fetchPipelines();
      } catch {
        setError("Delete failed");
      }
    }
    setConfirmAction(null);
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 left-0 z-50 w-96 bg-white shadow-xl flex flex-col transition-transform">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">
            Saved Pipelines
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close drawer"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && (
            <div className="flex items-center justify-center py-12 text-sm text-gray-400">
              <svg
                className="animate-spin h-5 w-5 mr-2 text-brand-500"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                />
              </svg>
              Loading...
            </div>
          )}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          {!loading && pipelines.length === 0 && !error && (
            <div className="text-center py-12 text-sm text-gray-400">
              No saved pipelines yet
            </div>
          )}

          {pipelines.map((pipeline) => (
            <div
              key={pipeline.id}
              className="border border-gray-200 rounded-lg p-4 hover:border-brand-300 transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-gray-800 truncate">
                    {pipeline.name}
                  </h3>
                  {pipeline.description && (
                    <p className="text-xs text-gray-500 mt-0.5 truncate">
                      {pipeline.description}
                    </p>
                  )}
                </div>
                <span
                  className={`ml-2 flex-shrink-0 inline-block px-2 py-0.5 text-xs font-medium rounded ${STATUS_BADGE[pipeline.status]}`}
                >
                  {pipeline.status}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
                <span className="inline-flex items-center gap-1 bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                  {pipeline.node_count} node{pipeline.node_count !== 1 ? "s" : ""}
                </span>
                <span>{formatDate(pipeline.updated_at)}</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleLoad(pipeline)}
                  className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-brand-600 hover:bg-brand-700 rounded transition-colors"
                >
                  Load
                </button>
                <button
                  onClick={() => handleDuplicate(pipeline)}
                  className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                >
                  Duplicate
                </button>
                <button
                  onClick={() => handleDelete(pipeline)}
                  className="px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Confirm Dialog */}
      {confirmAction && (
        <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h3 className="text-base font-semibold text-gray-800 mb-2">
              {confirmAction.type === "load"
                ? "Unsaved changes"
                : "Delete pipeline"}
            </h3>
            <p className="text-sm text-gray-600 mb-5">
              {confirmAction.type === "load"
                ? "You have unsaved changes. Loading a new pipeline will discard them. Continue?"
                : `Are you sure you want to delete "${confirmAction.pipeline.name}"? This action cannot be undone.`}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmAction(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={confirmActionHandler}
                className={`px-4 py-2 text-sm font-medium text-white rounded-md transition-colors ${
                  confirmAction.type === "delete"
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-brand-600 hover:bg-brand-700"
                }`}
              >
                {confirmAction.type === "load" ? "Load anyway" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
