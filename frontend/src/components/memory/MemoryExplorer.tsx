"use client";

import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import MemoryCard, { type MemoryItem } from "./MemoryCard";
import { SkeletonLoader } from "@/components/ui/LoadingSpinner";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface MemoryExplorerProps {
  /** Refresh trigger counter — increment to force reload */
  refreshKey?: number;
}

interface SearchFilters {
  query: string;
  scope: string;
  category: string;
  minImportance: number;
  showPrivate: boolean;
}

const CATEGORIES = [
  "fact",
  "decision",
  "observation",
  "alert",
  "preference",
  "context",
  "custom",
];
const SCOPES = ["workspace", "global"];

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function MemoryExplorer({ refreshKey = 0 }: MemoryExplorerProps) {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState<SearchFilters>({
    query: "",
    scope: "",
    category: "",
    minImportance: 1,
    showPrivate: false,
  });

  /* ---- Fetch ---- */
  const fetchMemories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number | boolean> = {};
      if (filters.query) params.q = filters.query;
      if (filters.scope) params.scope = filters.scope;
      if (filters.category) params.category = filters.category;
      if (filters.minImportance > 1)
        params.min_importance = filters.minImportance;
      if (filters.showPrivate) params.include_private = true;

      const res = await api.get<MemoryItem[]>("/api/memory/search", { params });
      setMemories(res.data);
    } catch {
      setError("Failed to load memories. Please try again.");
      setMemories([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories, refreshKey]);

  /* ---- Actions ---- */
  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/api/memory/${id}`);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch {
      // silent — TODO: toast
    }
  };

  const handleDecayNow = async (id: string) => {
    try {
      await api.post(`/api/memory/${id}/decay`);
      fetchMemories();
    } catch {
      // silent
    }
  };

  /* ---- Filter change helper ---- */
  const updateFilter = <K extends keyof SearchFilters>(
    key: K,
    value: SearchFilters[K],
  ) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  /* ---- Render ---- */
  return (
    <div className="space-y-4">
      {/* Search controls */}
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs text-gray-500">Search</label>
          <input
            value={filters.query}
            onChange={(e) => updateFilter("query", e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchMemories()}
            placeholder="Search memories..."
            className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          />
        </div>

        <div>
          <label className="text-xs text-gray-500">Scope</label>
          <select
            value={filters.scope}
            onChange={(e) => updateFilter("scope", e.target.value)}
            className="border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All</option>
            {SCOPES.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-gray-500">Category</label>
          <select
            value={filters.category}
            onChange={(e) => updateFilter("category", e.target.value)}
            className="border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c.charAt(0).toUpperCase() + c.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-gray-500">
            Min Importance: {filters.minImportance}
          </label>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            value={filters.minImportance}
            onChange={(e) => updateFilter("minImportance", Number(e.target.value))}
            className="w-24"
          />
        </div>

        <label className="flex items-center gap-1.5 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={filters.showPrivate}
            onChange={(e) => updateFilter("showPrivate", e.target.checked)}
            className="accent-brand-600"
          />
          Private
        </label>

        <button
          onClick={fetchMemories}
          className="px-4 py-2 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors"
        >
          Search
        </button>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="flex w-full rounded-xl border border-gray-200 bg-white p-4"
            >
              <div className="w-1.5 shrink-0 rounded-l-xl bg-gray-200 animate-pulse" />
              <div className="flex-1 ml-4">
                <SkeletonLoader lines={3} />
              </div>
              <div className="w-40 ml-4">
                <SkeletonLoader lines={2} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div className="text-center py-12">
          <p className="text-sm text-red-500 mb-3">{error}</p>
          <button
            onClick={fetchMemories}
            className="px-4 py-2 text-sm rounded-lg border border-red-300 text-red-600 hover:bg-red-50 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && memories.length === 0 && (
        <div className="text-center py-16">
          <div className="text-4xl mb-3 text-gray-300">
            <svg
              className="w-12 h-12 mx-auto"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <p className="text-sm text-gray-500">
            No memories found. Store your first memory to get started.
          </p>
        </div>
      )}

      {/* Memory cards */}
      {!loading && !error && memories.length > 0 && (
        <div className="space-y-3">
          {memories.map((m) => (
            <MemoryCard
              key={m.id}
              memory={m}
              onDelete={handleDelete}
              onDecayNow={handleDecayNow}
            />
          ))}
        </div>
      )}
    </div>
  );
}
