"use client";

import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import StoreMemoryModal from "@/components/memory/StoreMemoryModal";
import MemoryExplorer from "@/components/memory/MemoryExplorer";

/* ------------------------------------------------------------------ */
/* Lazy placeholders for components built by other agents              */
/* ------------------------------------------------------------------ */

// These components will be provided by parallel agents. Until then they
// render a placeholder so the page compiles and the tabs are wired.

function MemorySummaryTab({ summary }: { summary: Summary | null }) {
  if (!summary) {
    return <div className="text-center py-12 text-gray-400">Loading summary...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="border rounded-xl p-4">
          <p className="text-xs text-gray-500">Total Memories</p>
          <p className="text-2xl font-bold text-gray-900">{summary.total}</p>
        </div>
        <div className="border rounded-xl p-4">
          <p className="text-xs text-gray-500">Avg Importance</p>
          <p className="text-2xl font-bold text-brand-600">{summary.avg_importance.toFixed(3)}</p>
        </div>
        <div className="border rounded-xl p-4">
          <p className="text-xs text-gray-500">Avg Freshness</p>
          <p className="text-2xl font-bold text-green-600">{summary.avg_freshness.toFixed(3)}</p>
        </div>
        <div className="border rounded-xl p-4">
          <p className="text-xs text-gray-500">Stale Count</p>
          <p className="text-2xl font-bold text-amber-600">{summary.stale_count}</p>
        </div>
      </div>

      {/* By category */}
      <div className="border rounded-xl p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">By Category</h3>
        <div className="space-y-2">
          {Object.entries(summary.by_category).map(([cat, count]) => (
            <div key={cat} className="flex items-center gap-3">
              <span className="text-sm text-gray-700 w-28 capitalize">{cat}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-4">
                <div
                  className="bg-brand-500 h-4 rounded-full"
                  style={{ width: `${summary.total ? (count / summary.total) * 100 : 0}%` }}
                />
              </div>
              <span className="text-sm font-medium text-gray-600 w-10 text-right">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* By scope */}
      <div className="border rounded-xl p-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">By Scope</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(summary.by_scope).map(([scope, count]) => (
            <div key={scope} className="border rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 capitalize">{scope}</p>
              <p className="text-xl font-bold text-gray-800">{count}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Top memories */}
      {summary.top_memories.length > 0 && (
        <div className="border rounded-xl p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Top Memories</h3>
          <div className="space-y-2">
            {summary.top_memories.map((m) => (
              <div key={m.id} className="flex items-center gap-3 text-sm">
                <div className="w-full bg-gray-200 rounded-full h-2 flex-1">
                  <div
                    className="bg-brand-500 h-2 rounded-full"
                    style={{ width: `${Math.round(m.importance * 100)}%` }}
                  />
                </div>
                <span className="text-gray-700 truncate flex-1">{m.content}</span>
                <span className="text-xs text-gray-400 shrink-0">{m.importance.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MemoryTimelineTab() {
  return (
    <div className="text-center py-16 text-gray-400">
      <p className="text-sm">Timeline view — coming soon (MemoryTimelineTab)</p>
    </div>
  );
}

function MemoryConflictsTab() {
  return (
    <div className="text-center py-16 text-gray-400">
      <p className="text-sm">Conflict resolution — coming soon (MemoryConflictsTab)</p>
    </div>
  );
}

function MemoryNetworkGraph() {
  return (
    <div className="text-center py-16 text-gray-400">
      <p className="text-sm">Network graph — coming soon (MemoryNetworkGraph)</p>
    </div>
  );
}

function DecayRulesModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-semibold mb-4">Decay Rules</h2>
        <p className="text-sm text-gray-500">Decay rules configuration — coming soon.</p>
        <div className="mt-4 flex justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg border hover:bg-gray-50">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function MemoryDetailPanel({
  memoryId,
  onClose,
}: {
  memoryId: string | null;
  onClose: () => void;
}) {
  if (!memoryId) return null;
  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-white border-l border-gray-200 shadow-xl z-40 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Memory Detail</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">&times;</button>
      </div>
      <p className="text-sm text-gray-500">Detail panel — coming soon.</p>
      <p className="text-xs text-gray-400 mt-2 font-mono">{memoryId}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface Summary {
  total: number;
  by_category: Record<string, number>;
  by_scope: Record<string, number>;
  avg_importance: number;
  avg_freshness: number;
  top_memories: { id: string; content: string; importance: number }[];
  stale_count: number;
}

type TabKey = "explorer" | "summary" | "timeline" | "conflicts" | "network";

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function MemoryPage() {
  const [tab, setTab] = useState<TabKey>("explorer");
  const [storeOpen, setStoreOpen] = useState(false);
  const [decayRulesOpen, setDecayRulesOpen] = useState(false);
  const [detailMemoryId, setDetailMemoryId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [summary, setSummary] = useState<Summary | null>(null);

  /* ---- Summary loading ---- */
  const loadSummary = useCallback(async () => {
    try {
      const res = await api.get("/api/memory/summary");
      setSummary(res.data);
    } catch {
      setSummary(null);
    }
  }, []);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  /* ---- Actions ---- */
  const handleDecayAll = async () => {
    await api.post("/api/memory/decay", { decay_rate: 0.95 });
    setRefreshKey((k) => k + 1);
    loadSummary();
  };

  const handleApplyRules = async () => {
    try {
      const res = await api.post("/api/memory/apply-rules");
      alert(
        `Rules applied: ${res.data.promotions} promotions, ${res.data.demotions} demotions, ${res.data.archived} archived`,
      );
    } catch {
      // silent
    }
    setRefreshKey((k) => k + 1);
    loadSummary();
  };

  const handleExport = async () => {
    try {
      const res = await api.post("/api/memory/export");
      const blob = new Blob([JSON.stringify(res.data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "memories-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent
    }
  };

  const handleSaved = () => {
    setRefreshKey((k) => k + 1);
    loadSummary();
  };

  /* ---- Tabs config ---- */
  const TABS: { key: TabKey; label: string }[] = [
    { key: "explorer", label: "Explorer" },
    { key: "summary", label: "Summary" },
    { key: "timeline", label: "Timeline" },
    { key: "conflicts", label: "Conflicts" },
    { key: "network", label: "Network" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Semantic Memory</h1>
          <p className="text-sm text-gray-500 mt-1">
            Workspace-scoped long-term memory with scoring, decay, and conflict
            resolution
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleExport}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            Export
          </button>
          <button
            onClick={handleDecayAll}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            Decay All
          </button>
          <button
            onClick={handleApplyRules}
            className="px-3 py-2 text-sm rounded-lg border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-700"
          >
            Apply Rules
          </button>
          <button
            onClick={() => setDecayRulesOpen(true)}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            Decay Rules
          </button>
          <button
            onClick={() => setStoreOpen(true)}
            className="px-4 py-2 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700"
          >
            + Store Memory
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-brand-600 text-brand-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "explorer" && <MemoryExplorer refreshKey={refreshKey} />}
      {tab === "summary" && <MemorySummaryTab summary={summary} />}
      {tab === "timeline" && <MemoryTimelineTab />}
      {tab === "conflicts" && <MemoryConflictsTab />}
      {tab === "network" && <MemoryNetworkGraph />}

      {/* Modals & panels */}
      <StoreMemoryModal
        isOpen={storeOpen}
        onClose={() => setStoreOpen(false)}
        onSaved={handleSaved}
      />
      <DecayRulesModal
        isOpen={decayRulesOpen}
        onClose={() => setDecayRulesOpen(false)}
      />
      <MemoryDetailPanel
        memoryId={detailMemoryId}
        onClose={() => setDetailMemoryId(null)}
      />
    </div>
  );
}
