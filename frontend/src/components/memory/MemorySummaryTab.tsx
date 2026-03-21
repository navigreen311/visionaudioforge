"use client";

import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface SummaryStats {
  total: number;
  avg_importance: number;
  high_importance_count: number;
  private_count: number;
  by_category: Record<string, number>;
  importance_distribution: { bucket: string; count: number; level: "low" | "medium" | "high" | "critical" }[];
  freshness_distribution: { label: string; count: number; color: "green" | "yellow" | "orange" | "red" }[];
}

const CATEGORY_COLORS: Record<string, string> = {
  fact: "#3b82f6",
  event: "#22c55e",
  preference: "#a855f7",
  rule: "#eab308",
  entity: "#ec4899",
  relationship: "#6366f1",
};

const LEVEL_COLORS: Record<string, string> = {
  low: "#94a3b8",
  medium: "#3b82f6",
  high: "#f59e0b",
  critical: "#ef4444",
};

const FRESHNESS_PILL_COLORS: Record<string, string> = {
  green: "bg-green-100 text-green-700",
  yellow: "bg-yellow-100 text-yellow-700",
  orange: "bg-orange-100 text-orange-700",
  red: "bg-red-100 text-red-700",
};

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function MemorySummaryTab() {
  const [stats, setStats] = useState<SummaryStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [decaying, setDecaying] = useState(false);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/memory/summary");
      setStats(res.data);
    } catch {
      setStats(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const handleDecayAll = async () => {
    if (!window.confirm("Apply decay to all memories? This will reduce freshness scores across the board.")) {
      return;
    }
    setDecaying(true);
    try {
      await api.post("/api/memory/decay-all");
      await loadSummary();
    } catch {
      // silently handle
    }
    setDecaying(false);
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Loading summary...</div>;
  }

  if (!stats) {
    return <div className="text-center py-12 text-gray-400">Unable to load summary data.</div>;
  }

  /* ---- SVG helpers ---- */
  const categoryEntries = Object.entries(stats.by_category);
  const categoryTotal = categoryEntries.reduce((sum, [, count]) => sum + count, 0);

  const histogramMax = Math.max(...stats.importance_distribution.map((b) => b.count), 1);
  const histBarWidth = stats.importance_distribution.length > 0 ? 300 / stats.importance_distribution.length - 4 : 40;

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="border rounded-xl p-4">
          <p className="text-xs text-gray-500">Total Memories</p>
          <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
        </div>
        <div className="border rounded-xl p-4">
          <p className="text-xs text-gray-500">Avg Importance</p>
          <p className="text-2xl font-bold text-brand-600">{stats.avg_importance.toFixed(3)}</p>
        </div>
        <div className="border rounded-xl p-4">
          <p className="text-xs text-gray-500">High Importance</p>
          <p className="text-2xl font-bold text-amber-600">{stats.high_importance_count}</p>
        </div>
        <div className="border rounded-xl p-4">
          <p className="text-xs text-gray-500">Private</p>
          <p className="text-2xl font-bold text-red-600">{stats.private_count}</p>
        </div>
      </div>

      {/* Category breakdown — SVG horizontal bar chart */}
      <div className="border rounded-xl p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Category Breakdown</h3>
        {categoryEntries.length === 0 ? (
          <p className="text-sm text-gray-400">No categories yet.</p>
        ) : (
          <svg
            width="100%"
            viewBox={`0 0 400 ${categoryEntries.length * 28}`}
            className="overflow-visible"
            aria-label="Category breakdown chart"
          >
            {categoryEntries.map(([cat, count], i) => {
              const barWidth = categoryTotal > 0 ? (count / categoryTotal) * 280 : 0;
              const y = i * 28;
              return (
                <g key={cat}>
                  <text x={0} y={y + 16} fill="#6b7280" fontSize={12}>
                    {cat}
                  </text>
                  <rect
                    x={80}
                    y={y + 4}
                    width={barWidth}
                    height={18}
                    rx={4}
                    fill={CATEGORY_COLORS[cat] || "#9ca3af"}
                  />
                  <text x={80 + barWidth + 6} y={y + 16} fill="#374151" fontSize={12} fontWeight={600}>
                    {count}
                  </text>
                </g>
              );
            })}
          </svg>
        )}
      </div>

      {/* Importance distribution — SVG histogram */}
      <div className="border rounded-xl p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Importance Distribution</h3>
        <svg width="300" height="160" viewBox="0 0 300 160" aria-label="Importance distribution histogram">
          {stats.importance_distribution.map((bucket, i) => {
            const barHeight = histogramMax > 0 ? (bucket.count / histogramMax) * 130 : 0;
            const x = i * (histBarWidth + 4) + 2;
            return (
              <g key={bucket.bucket}>
                <rect
                  x={x}
                  y={130 - barHeight}
                  width={histBarWidth}
                  height={barHeight}
                  rx={2}
                  fill={LEVEL_COLORS[bucket.level] || "#9ca3af"}
                />
                <text
                  x={x + histBarWidth / 2}
                  y={148}
                  textAnchor="middle"
                  fill="#6b7280"
                  fontSize={9}
                >
                  {bucket.bucket}
                </text>
                <text
                  x={x + histBarWidth / 2}
                  y={126 - barHeight}
                  textAnchor="middle"
                  fill="#374151"
                  fontSize={9}
                  fontWeight={600}
                >
                  {bucket.count}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Freshness distribution pills */}
      <div className="border rounded-xl p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Freshness Distribution</h3>
        <div className="flex flex-wrap gap-3">
          {stats.freshness_distribution.map((bucket) => (
            <span
              key={bucket.label}
              className={`px-3 py-1.5 rounded-full text-sm font-medium ${FRESHNESS_PILL_COLORS[bucket.color] || "bg-gray-100 text-gray-700"}`}
            >
              {bucket.label}: {bucket.count}
            </span>
          ))}
        </div>
      </div>

      {/* Decay All action */}
      <div className="flex justify-end">
        <button
          onClick={handleDecayAll}
          disabled={decaying}
          className="px-4 py-2 text-sm rounded-lg border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-700 disabled:opacity-50"
        >
          {decaying ? "Decaying..." : "Decay All"}
        </button>
      </div>
    </div>
  );
}
