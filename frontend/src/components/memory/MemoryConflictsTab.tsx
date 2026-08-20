"use client";

import { API_BASE_URL } from "@/lib/api";

import { useState, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MemoryItem {
  id: string;
  content: string;
  category: string;
  importance: number;
  created_at: number;
  metadata: Record<string, unknown>;
}

interface MemoryConflict {
  id: string;
  memory_a: MemoryItem;
  memory_b: MemoryItem;
  conflict_type: string;
  similarity: number;
  detected_at: number;
}

type ResolutionAction = "keep_a" | "keep_b" | "merge" | "ignore";

interface ResolvePayload {
  action: ResolutionAction;
  merged_content?: string;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const API_BASE = API_BASE_URL;

async function fetchConflicts(): Promise<MemoryConflict[]> {
  const res = await fetch(`${API_BASE}/api/memory/conflicts`);
  if (!res.ok) throw new Error(`Failed to fetch conflicts: ${res.status}`);
  const data: { conflicts: MemoryConflict[] } = await res.json();
  return data.conflicts;
}

async function resolveConflict(
  conflictId: string,
  payload: ResolvePayload,
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/memory/conflicts/${conflictId}/resolve`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  if (!res.ok) throw new Error(`Failed to resolve conflict: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MemoryCard({
  memory,
  side,
  highlight,
}: {
  memory: MemoryItem;
  side: "A" | "B";
  highlight: boolean;
}) {
  const borderColor = highlight
    ? side === "A"
      ? "border-blue-500"
      : "border-amber-500"
    : "border-gray-700";

  return (
    <div
      className={`flex-1 rounded-lg border-2 ${borderColor} bg-gray-800 p-4`}
    >
      <div className="mb-2 flex items-center justify-between">
        <span
          className={`rounded px-2 py-0.5 text-xs font-semibold ${
            side === "A"
              ? "bg-blue-900 text-blue-300"
              : "bg-amber-900 text-amber-300"
          }`}
        >
          Memory {side}
        </span>
        <span className="text-xs text-gray-400">{memory.category}</span>
      </div>
      <p className="mb-3 text-sm text-gray-200">{memory.content}</p>
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>Importance: {(memory.importance * 100).toFixed(0)}%</span>
        <span>
          Created: {new Date(memory.created_at * 1000).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
}

function MergeEditor({
  initialContent,
  onSave,
  onCancel,
}: {
  initialContent: string;
  onSave: (merged: string) => void;
  onCancel: () => void;
}) {
  const [content, setContent] = useState(initialContent);

  return (
    <div className="mt-3 rounded-lg border border-gray-600 bg-gray-900 p-3">
      <label className="mb-1 block text-xs font-medium text-gray-400">
        Merged content
      </label>
      <textarea
        className="w-full rounded border border-gray-600 bg-gray-800 p-2 text-sm text-gray-200 focus:border-indigo-500 focus:outline-none"
        rows={4}
        value={content}
        onChange={(e) => setContent(e.target.value)}
      />
      <div className="mt-2 flex gap-2">
        <button
          onClick={() => onSave(content)}
          className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-500"
        >
          Save Merge
        </button>
        <button
          onClick={onCancel}
          className="rounded bg-gray-700 px-3 py-1 text-xs text-gray-300 hover:bg-gray-600"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function MemoryConflictsTab() {
  const [conflicts, setConflicts] = useState<MemoryConflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [mergingId, setMergingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchConflicts();
      setConflicts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleResolve = useCallback(
    async (conflictId: string, action: ResolutionAction, merged?: string) => {
      setResolvingId(conflictId);
      try {
        const payload: ResolvePayload = { action };
        if (action === "merge" && merged) {
          payload.merged_content = merged;
        }
        await resolveConflict(conflictId, payload);
        setConflicts((prev) => prev.filter((c) => c.id !== conflictId));
        setMergingId(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Resolution failed");
      } finally {
        setResolvingId(null);
      }
    },
    [],
  );

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-100">
          {loading
            ? "Checking for conflicts..."
            : conflicts.length > 0
              ? `${conflicts.length} conflict${conflicts.length > 1 ? "s" : ""} detected`
              : "No conflicts \u2713"}
        </h2>
        <button
          onClick={load}
          disabled={loading}
          className="rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded border border-red-700 bg-red-900/30 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading && (
        <div className="py-12 text-center text-gray-500">Loading...</div>
      )}

      {!loading && conflicts.length === 0 && !error && (
        <div className="rounded-lg border border-green-800 bg-green-900/20 py-10 text-center text-green-400">
          All memories are consistent. No conflicts found.
        </div>
      )}

      {/* Conflict cards */}
      {conflicts.map((conflict) => {
        const isResolving = resolvingId === conflict.id;
        const isMerging = mergingId === conflict.id;

        return (
          <div
            key={conflict.id}
            className="rounded-xl border border-gray-700 bg-gray-850 p-5"
          >
            {/* Conflict metadata */}
            <div className="mb-3 flex items-center gap-3 text-xs text-gray-400">
              <span className="rounded bg-red-900/50 px-2 py-0.5 text-red-300">
                {conflict.conflict_type}
              </span>
              <span>
                Similarity: {(conflict.similarity * 100).toFixed(0)}%
              </span>
            </div>

            {/* Side-by-side cards */}
            <div className="flex gap-4">
              <MemoryCard memory={conflict.memory_a} side="A" highlight />
              <MemoryCard memory={conflict.memory_b} side="B" highlight />
            </div>

            {/* Merge editor */}
            {isMerging && (
              <MergeEditor
                initialContent={`${conflict.memory_a.content}\n---\n${conflict.memory_b.content}`}
                onSave={(merged) =>
                  handleResolve(conflict.id, "merge", merged)
                }
                onCancel={() => setMergingId(null)}
              />
            )}

            {/* Action buttons */}
            <div className="mt-4 flex gap-2">
              <button
                disabled={isResolving}
                onClick={() => handleResolve(conflict.id, "keep_a")}
                className="rounded bg-blue-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-600 disabled:opacity-50"
              >
                Keep A
              </button>
              <button
                disabled={isResolving}
                onClick={() => handleResolve(conflict.id, "keep_b")}
                className="rounded bg-amber-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600 disabled:opacity-50"
              >
                Keep B
              </button>
              <button
                disabled={isResolving}
                onClick={() => setMergingId(conflict.id)}
                className="rounded bg-indigo-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
              >
                Merge
              </button>
              <button
                disabled={isResolving}
                onClick={() => handleResolve(conflict.id, "ignore")}
                className="rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600 disabled:opacity-50"
              >
                Ignore
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
