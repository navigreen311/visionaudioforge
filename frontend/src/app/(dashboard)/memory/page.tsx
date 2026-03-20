"use client";

import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */
interface Memory {
  id: string;
  content: string;
  category: string;
  scope: string;
  importance_score: number;
  freshness_score: number;
  access_count: number;
  source: string | null;
  source_type: string;
  confidence: number;
  is_private: boolean;
  tags: string[];
  created_at: string | null;
}

interface Summary {
  total: number;
  by_category: Record<string, number>;
  by_scope: Record<string, number>;
  avg_importance: number;
  avg_freshness: number;
  top_memories: { id: string; content: string; importance: number }[];
  stale_count: number;
}

const CATEGORIES = ["fact", "event", "preference", "rule", "entity", "relationship"];
const SCOPES = ["global", "workspace", "user", "agent"];

const CATEGORY_COLORS: Record<string, string> = {
  fact: "bg-blue-500",
  event: "bg-green-500",
  preference: "bg-purple-500",
  rule: "bg-yellow-500",
  entity: "bg-pink-500",
  relationship: "bg-indigo-500",
};

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */
export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"explorer" | "summary" | "timeline" | "conflicts">("explorer");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [filterScope, setFilterScope] = useState<string>("");
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [minImportance, setMinImportance] = useState(0);
  const [showPrivate, setShowPrivate] = useState(false);

  // Detail / conflict
  const [selected, setSelected] = useState<Memory | null>(null);
  const [conflictA, setConflictA] = useState<string>("");
  const [conflictB, setConflictB] = useState<string>("");

  // Store form
  const [storeOpen, setStoreOpen] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("fact");
  const [newScope, setNewScope] = useState("workspace");
  const [newTags, setNewTags] = useState("");
  const [newImportance, setNewImportance] = useState(0.5);

  // Timeline
  const [timelineStart, setTimelineStart] = useState("");
  const [timelineEnd, setTimelineEnd] = useState("");
  const [timelineMemories, setTimelineMemories] = useState<Memory[]>([]);

  /* ---- Data loading ---- */
  const loadMemories = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.post("/api/memory/recall", {
        query: searchQuery || "",
        scope: filterScope || undefined,
        category: filterCategory || undefined,
        k: 50,
        min_importance: minImportance,
        include_private: showPrivate,
      });
      setMemories(res.data);
    } catch {
      setMemories([]);
    }
    setLoading(false);
  }, [searchQuery, filterScope, filterCategory, minImportance, showPrivate]);

  const loadSummary = useCallback(async () => {
    try {
      const res = await api.get("/api/memory/summary");
      setSummary(res.data);
    } catch {
      setSummary(null);
    }
  }, []);

  useEffect(() => {
    loadMemories();
    loadSummary();
  }, [loadMemories, loadSummary]);

  /* ---- Actions ---- */
  const handleStore = async () => {
    await api.post("/api/memory/store", {
      content: newContent,
      category: newCategory,
      scope: newScope,
      importance: newImportance,
      tags: newTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    });
    setStoreOpen(false);
    setNewContent("");
    setNewTags("");
    loadMemories();
    loadSummary();
  };

  const handlePromote = async (id: string) => {
    await api.post(`/api/memory/promote/${id}`, { boost: 0.2 });
    loadMemories();
  };

  const handleDemote = async (id: string) => {
    await api.post(`/api/memory/demote/${id}`, { boost: 0.2 });
    loadMemories();
  };

  const handleDecay = async () => {
    await api.post("/api/memory/decay", { decay_rate: 0.95 });
    loadMemories();
    loadSummary();
  };

  const handleApplyRules = async () => {
    const res = await api.post("/api/memory/apply-rules");
    alert(`Rules applied: ${res.data.promotions} promotions, ${res.data.demotions} demotions, ${res.data.archived} archived`);
    loadMemories();
    loadSummary();
  };

  const handleResolveConflict = async () => {
    if (!conflictA || !conflictB) return;
    await api.post("/api/memory/resolve-conflict", {
      memory_a_id: conflictA,
      memory_b_id: conflictB,
    });
    setConflictA("");
    setConflictB("");
    loadMemories();
  };

  const handleExport = async () => {
    const res = await api.post("/api/memory/export");
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "memories-export.json";
    a.click();
  };

  const loadTimeline = async () => {
    if (!timelineStart || !timelineEnd) return;
    const res = await api.get("/api/memory/timeline", {
      params: { start: timelineStart, end: timelineEnd },
    });
    setTimelineMemories(res.data);
  };

  /* ---- Bar helper ---- */
  const Bar = ({ value, color }: { value: number; color: string }) => (
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div
        className={`${color} h-2 rounded-full transition-all`}
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );

  /* ---- Render ---- */
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Semantic Memory</h1>
          <p className="text-sm text-gray-500 mt-1">
            Workspace-scoped long-term memory with scoring, decay, and conflict resolution
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExport} className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
            Export
          </button>
          <button onClick={handleDecay} className="px-3 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50">
            Decay All
          </button>
          <button onClick={handleApplyRules} className="px-3 py-2 text-sm rounded-lg border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-700">
            Apply Rules
          </button>
          <button onClick={() => setStoreOpen(true)} className="px-4 py-2 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700">
            + Store Memory
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {(["explorer", "summary", "timeline", "conflicts"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? "border-brand-600 text-brand-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Store modal */}
      {storeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg space-y-4">
            <h2 className="text-lg font-semibold">Store New Memory</h2>
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Memory content..."
              className="w-full border rounded-lg p-3 text-sm h-24"
            />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">Category</label>
                <select value={newCategory} onChange={(e) => setNewCategory(e.target.value)} className="w-full border rounded p-2 text-sm">
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500">Scope</label>
                <select value={newScope} onChange={(e) => setNewScope(e.target.value)} className="w-full border rounded p-2 text-sm">
                  {SCOPES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500">Tags (comma-separated)</label>
              <input value={newTags} onChange={(e) => setNewTags(e.target.value)} className="w-full border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-gray-500">Importance: {newImportance}</label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={newImportance}
                onChange={(e) => setNewImportance(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setStoreOpen(false)} className="px-4 py-2 text-sm rounded-lg border hover:bg-gray-50">Cancel</button>
              <button onClick={handleStore} disabled={!newContent} className="px-4 py-2 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50">
                Store
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---- Explorer Tab ---- */}
      {tab === "explorer" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="text-xs text-gray-500">Search</label>
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadMemories()}
                placeholder="Search memories..."
                className="w-full border rounded-lg p-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">Scope</label>
              <select value={filterScope} onChange={(e) => setFilterScope(e.target.value)} className="border rounded p-2 text-sm">
                <option value="">All</option>
                {SCOPES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Category</label>
              <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)} className="border rounded p-2 text-sm">
                <option value="">All</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Min Importance</label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={minImportance}
                onChange={(e) => setMinImportance(parseFloat(e.target.value))}
                className="w-24"
              />
              <span className="text-xs text-gray-500 ml-1">{minImportance}</span>
            </div>
            <label className="flex items-center gap-1 text-sm">
              <input type="checkbox" checked={showPrivate} onChange={(e) => setShowPrivate(e.target.checked)} />
              Private
            </label>
            <button onClick={loadMemories} className="px-3 py-2 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700">
              Search
            </button>
          </div>

          {/* Memory list */}
          {loading ? (
            <div className="text-center py-12 text-gray-400">Loading...</div>
          ) : memories.length === 0 ? (
            <div className="text-center py-12 text-gray-400">No memories found. Store your first memory above.</div>
          ) : (
            <div className="grid gap-3">
              {memories.map((m) => (
                <div
                  key={m.id}
                  onClick={() => setSelected(selected?.id === m.id ? null : m)}
                  className={`border rounded-xl p-4 cursor-pointer transition-colors ${
                    selected?.id === m.id ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`inline-block w-2 h-2 rounded-full ${CATEGORY_COLORS[m.category] || "bg-gray-400"}`} />
                        <span className="text-xs font-medium text-gray-500 uppercase">{m.category}</span>
                        <span className="text-xs text-gray-400">|</span>
                        <span className="text-xs text-gray-400">{m.scope}</span>
                        {m.is_private && <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">Private</span>}
                      </div>
                      <p className="text-sm text-gray-800 line-clamp-2">{m.content}</p>
                      {m.tags.length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {m.tags.map((t) => (
                            <span key={t} className="text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-2 w-32 shrink-0">
                      <div>
                        <span className="text-[10px] text-gray-500">Importance</span>
                        <Bar value={m.importance_score} color="bg-brand-500" />
                      </div>
                      <div>
                        <span className="text-[10px] text-gray-500">Freshness</span>
                        <Bar value={m.freshness_score} color="bg-green-500" />
                      </div>
                    </div>
                  </div>

                  {/* Detail panel */}
                  {selected?.id === m.id && (
                    <div className="mt-4 pt-4 border-t border-gray-200 space-y-3">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                        <div><span className="text-gray-500">Confidence:</span> {m.confidence}</div>
                        <div><span className="text-gray-500">Access count:</span> {m.access_count}</div>
                        <div><span className="text-gray-500">Source:</span> {m.source || "N/A"}</div>
                        <div><span className="text-gray-500">Source type:</span> {m.source_type}</div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={(e) => { e.stopPropagation(); handlePromote(m.id); }} className="px-3 py-1.5 text-xs rounded-lg bg-green-50 text-green-700 border border-green-200 hover:bg-green-100">
                          Promote +0.2
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); handleDemote(m.id); }} className="px-3 py-1.5 text-xs rounded-lg bg-red-50 text-red-700 border border-red-200 hover:bg-red-100">
                          Demote -0.2
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ---- Summary Tab ---- */}
      {tab === "summary" && summary && (
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
                  <span className={`w-3 h-3 rounded-full ${CATEGORY_COLORS[cat] || "bg-gray-400"}`} />
                  <span className="text-sm text-gray-700 w-28">{cat}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-4">
                    <div
                      className={`${CATEGORY_COLORS[cat] || "bg-gray-400"} h-4 rounded-full`}
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
                  <p className="text-xs text-gray-500">{scope}</p>
                  <p className="text-xl font-bold text-gray-800">{count}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Top memories */}
          <div className="border rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Top Memories</h3>
            <div className="space-y-2">
              {summary.top_memories.map((m) => (
                <div key={m.id} className="flex items-center gap-3 text-sm">
                  <Bar value={m.importance} color="bg-brand-500" />
                  <span className="text-gray-700 truncate flex-1">{m.content}</span>
                  <span className="text-xs text-gray-400 shrink-0">{m.importance.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ---- Timeline Tab ---- */}
      {tab === "timeline" && (
        <div className="space-y-4">
          <div className="flex gap-3 items-end">
            <div>
              <label className="text-xs text-gray-500">Start</label>
              <input type="datetime-local" value={timelineStart} onChange={(e) => setTimelineStart(e.target.value)} className="border rounded p-2 text-sm" />
            </div>
            <div>
              <label className="text-xs text-gray-500">End</label>
              <input type="datetime-local" value={timelineEnd} onChange={(e) => setTimelineEnd(e.target.value)} className="border rounded p-2 text-sm" />
            </div>
            <button onClick={loadTimeline} className="px-4 py-2 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700">
              Load
            </button>
          </div>

          {timelineMemories.length === 0 ? (
            <div className="text-center py-12 text-gray-400">Select a date range and click Load.</div>
          ) : (
            <div className="relative pl-6 border-l-2 border-gray-200 space-y-4">
              {timelineMemories.map((m) => (
                <div key={m.id} className="relative">
                  <div className="absolute -left-[29px] top-1 w-3 h-3 rounded-full bg-brand-500 border-2 border-white" />
                  <div className="border rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-gray-400">{m.created_at ? new Date(m.created_at).toLocaleString() : ""}</span>
                      <span className={`w-2 h-2 rounded-full ${CATEGORY_COLORS[m.category] || "bg-gray-400"}`} />
                      <span className="text-xs text-gray-500">{m.category}</span>
                    </div>
                    <p className="text-sm text-gray-800">{m.content}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ---- Conflicts Tab ---- */}
      {tab === "conflicts" && (
        <div className="space-y-6">
          <div className="border rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">Resolve Conflict</h3>
            <p className="text-xs text-gray-500 mb-3">
              Enter two memory IDs to compare. The higher-confidence memory wins; content is merged if complementary.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500">Memory A ID</label>
                <input value={conflictA} onChange={(e) => setConflictA(e.target.value)} className="w-full border rounded p-2 text-sm" placeholder="UUID..." />
              </div>
              <div>
                <label className="text-xs text-gray-500">Memory B ID</label>
                <input value={conflictB} onChange={(e) => setConflictB(e.target.value)} className="w-full border rounded p-2 text-sm" placeholder="UUID..." />
              </div>
            </div>
            <button
              onClick={handleResolveConflict}
              disabled={!conflictA || !conflictB}
              className="mt-3 px-4 py-2 text-sm rounded-lg bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-50"
            >
              Resolve Conflict
            </button>
          </div>

          {/* List all memories for easy ID reference */}
          <div className="border rounded-xl p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">All Memories (for reference)</h3>
            <div className="max-h-96 overflow-y-auto space-y-2">
              {memories.map((m) => (
                <div key={m.id} className="flex items-center gap-3 text-xs border-b pb-2">
                  <code className="text-gray-400 font-mono text-[10px] shrink-0">{m.id.slice(0, 8)}...</code>
                  <span className={`w-2 h-2 rounded-full ${CATEGORY_COLORS[m.category] || "bg-gray-400"}`} />
                  <span className="truncate text-gray-700">{m.content}</span>
                  <span className="shrink-0 text-gray-400">c={m.confidence}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
