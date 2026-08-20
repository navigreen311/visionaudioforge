"use client";


import { useState, useEffect, useCallback, useRef } from "react";
// The shared client from lib/api.ts, not the bare axios module: the request
// interceptor that attaches the session token lives on that instance, so a
// direct `axios.get` reached the API with no Authorization header and was
// answered 401. Its baseURL is API_BASE_URL, so paths here are relative.
import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface ModelItem {
  id: string;
  name: string;
  version: string;
  status: string;
  backbone: string | null;
  metrics: Record<string, number> | null;
  tags: string[] | null;
  description: string | null;
  workspace_id: string;
  created_at: string;
  updated_at: string;
}

interface PaginatedModels {
  items: ModelItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface ModelRegistryTableProps {
  workspaceId: string;
  onRegisterClick: () => void;
  refreshKey?: number;
  onViewDetail?: (model: ModelItem) => void;
  onCompare?: (model: ModelItem, allModels: ModelItem[]) => void;
}

export type { ModelItem };

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<string, string> = {
  registered: "bg-gray-100 text-gray-700",
  staging: "bg-amber-100 text-amber-800",
  production: "bg-emerald-100 text-emerald-800",
  shadow: "bg-blue-100 text-blue-800",
  archived: "bg-gray-300 text-gray-600",
};

const BACKBONE_COLORS: Record<string, string> = {
  ResNet18: "bg-indigo-50 text-indigo-700 border-indigo-200",
  ResNet50: "bg-indigo-50 text-indigo-700 border-indigo-200",
  "ViT-B/16": "bg-violet-50 text-violet-700 border-violet-200",
  "EfficientNet-B0": "bg-teal-50 text-teal-700 border-teal-200",
  "CLIP ViT-B/32": "bg-pink-50 text-pink-700 border-pink-200",
  "Whisper-Small": "bg-orange-50 text-orange-700 border-orange-200",
  Wav2Vec2: "bg-cyan-50 text-cyan-700 border-cyan-200",
  CLAP: "bg-rose-50 text-rose-700 border-rose-200",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

function trendArrow(value: number | undefined): string {
  if (value === undefined) return "";
  if (value >= 0.9) return "\u2191"; // up arrow
  if (value >= 0.7) return "\u2192"; // right arrow
  return "\u2193"; // down arrow
}

function trendColor(value: number | undefined): string {
  if (value === undefined) return "text-gray-400";
  if (value >= 0.9) return "text-emerald-600";
  if (value >= 0.7) return "text-amber-600";
  return "text-red-600";
}

// ---------------------------------------------------------------------------
// Action menu
// ---------------------------------------------------------------------------
function ActionMenu({
  model,
  onAction,
}: {
  model: ModelItem;
  onAction: (action: string, model: ModelItem) => void;
}) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const actions = [
    { key: "view", label: "View Detail" },
    { key: "promote", label: "Promote" },
    { key: "compare", label: "Compare" },
    { key: "rollback", label: "Rollback" },
    { key: "archive", label: "Archive" },
  ];

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        className="p-1 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
        aria-label="Actions"
      >
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <circle cx="10" cy="4" r="1.5" />
          <circle cx="10" cy="10" r="1.5" />
          <circle cx="10" cy="16" r="1.5" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-8 z-20 w-40 rounded-lg border border-gray-200 bg-white shadow-lg py-1">
          {actions.map((a) => (
            <button
              key={a.key}
              onClick={(e) => {
                e.stopPropagation();
                setOpen(false);
                onAction(a.key, model);
              }}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function ModelRegistryTable({
  workspaceId,
  onRegisterClick,
  refreshKey = 0,
  onViewDetail,
  onCompare,
}: ModelRegistryTableProps) {
  const [models, setModels] = useState<ModelItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const fetchModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ workspace_id: workspaceId });
      if (statusFilter) params.set("status", statusFilter);
      const resp = await api.get<PaginatedModels>(
        `/api/registry/models?${params.toString()}`
      );
      setModels(resp.data.items || []);
    } catch (err) {
      console.error("Failed to load models", err);
      setError("Failed to load models. Is the backend running?");
      setModels([]);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, statusFilter]);

  useEffect(() => {
    fetchModels();
  }, [fetchModels, refreshKey]);

  const handleAction = async (action: string, model: ModelItem) => {
    switch (action) {
      case "archive":
        try {
          await api.put(`/api/registry/models/${model.id}/status`, {
            status: "archived",
          });
          fetchModels();
        } catch (err) {
          console.error("Archive failed", err);
        }
        break;
      case "promote":
        try {
          await api.put(`/api/registry/models/${model.id}/status`, {
            status: "production",
          });
          fetchModels();
        } catch (err) {
          console.error("Promote failed", err);
        }
        break;
      case "view":
        onViewDetail?.(model);
        break;
      case "compare":
        onCompare?.(model, models);
        break;
      default:
        // rollback -- placeholder
        console.log(`Action "${action}" on model ${model.id}`);
    }
  };

  // Status filter chips
  const statuses = ["registered", "staging", "production", "shadow", "archived"];

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setStatusFilter(null)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-colors ${
              statusFilter === null
                ? "bg-[#185FA5] text-white border-[#185FA5]"
                : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
            }`}
          >
            All
          </button>
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-colors capitalize ${
                statusFilter === s
                  ? "bg-[#185FA5] text-white border-[#185FA5]"
                  : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <button
          onClick={onRegisterClick}
          className="px-4 py-2 bg-[#185FA5] text-white text-sm font-medium rounded-lg hover:bg-[#14508a] transition-colors"
        >
          Register Model
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin h-6 w-6 border-2 border-[#185FA5] border-t-transparent rounded-full" />
          <span className="ml-3 text-sm text-gray-500">Loading models...</span>
        </div>
      ) : error ? (
        <div className="text-center py-16">
          <p className="text-sm text-red-500">{error}</p>
          <button
            onClick={fetchModels}
            className="mt-2 text-sm text-[#185FA5] hover:underline"
          >
            Retry
          </button>
        </div>
      ) : models.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">
            No models registered
          </h3>
          <p className="mt-1 max-w-sm text-sm text-gray-500">
            Register your first model to start tracking versions, metrics, and
            lifecycle stages.
          </p>
          <button
            onClick={onRegisterClick}
            className="mt-4 px-4 py-2 bg-[#185FA5] text-white text-sm font-medium rounded-lg hover:bg-[#14508a] transition-colors"
          >
            Register Model
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Version</th>
                <th className="text-left px-4 py-3">Backbone</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Metrics</th>
                <th className="text-left px-4 py-3">Registered</th>
                <th className="text-right px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {models.map((m) => {
                const valAcc = m.metrics?.val_accuracy as number | undefined;
                return (
                  <tr
                    key={m.id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    {/* Name */}
                    <td className="px-4 py-3">
                      <span className="font-semibold text-gray-900">
                        {m.name}
                      </span>
                    </td>
                    {/* Version */}
                    <td className="px-4 py-3 text-gray-600">{m.version}</td>
                    {/* Backbone */}
                    <td className="px-4 py-3">
                      {m.backbone ? (
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${
                            BACKBONE_COLORS[m.backbone] ||
                            "bg-gray-50 text-gray-700 border-gray-200"
                          }`}
                        >
                          {m.backbone}
                        </span>
                      ) : (
                        <span className="text-gray-400">--</span>
                      )}
                    </td>
                    {/* Status */}
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${
                          STATUS_STYLES[m.status] || STATUS_STYLES.registered
                        }`}
                      >
                        {m.status}
                      </span>
                    </td>
                    {/* Metrics */}
                    <td className="px-4 py-3">
                      {valAcc !== undefined ? (
                        <span className="flex items-center gap-1 text-gray-700">
                          <span className="font-mono text-xs">
                            {(valAcc * 100).toFixed(1)}%
                          </span>
                          <span
                            className={`text-xs font-bold ${trendColor(valAcc)}`}
                          >
                            {trendArrow(valAcc)}
                          </span>
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">--</span>
                      )}
                    </td>
                    {/* Registered */}
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {relativeDate(m.created_at)}
                    </td>
                    {/* Actions */}
                    <td className="px-4 py-3 text-right">
                      <ActionMenu model={m} onAction={handleAction} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
