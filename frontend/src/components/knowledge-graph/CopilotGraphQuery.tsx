"use client";

import { useState, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CopilotGraphQueryProps {
  nodeCount: number;
  edgeCount: number;
  nodeTypes: string[];
  onHighlight: (nodeNames: string[]) => void;
}

interface QueryResponse {
  response: string;
  agent_id: string;
  memories_used: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extract words that could be node labels from the response text. */
function extractMentionedNames(
  text: string,
  nodeTypes: string[],
): string[] {
  // Look for capitalized multi-word names and single capitalized words
  const namePattern = /\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*/g;
  const matches = text.match(namePattern) ?? [];
  // Filter out type labels themselves
  const typeSet = new Set(nodeTypes.map((t) => t.toLowerCase()));
  return matches.filter((m) => !typeSet.has(m.toLowerCase()));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CopilotGraphQuery({
  nodeCount,
  edgeCount,
  nodeTypes,
  onHighlight,
}: CopilotGraphQueryProps) {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!query.trim()) return;

      setLoading(true);
      setError(null);
      setResponse(null);
      onHighlight([]);

      try {
        const res = await fetch("/api/agents/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: query,
            skill_pack: "knowledge-graph",
            context: {
              source: "knowledge-graph",
              node_count: nodeCount,
              edge_count: edgeCount,
              node_types: nodeTypes,
            },
          }),
        });

        if (!res.ok) throw new Error(`Query failed: ${res.status}`);
        const data = (await res.json()) as QueryResponse;
        setResponse(data.response);

        // Auto-highlight matching node names
        const names = extractMentionedNames(data.response, nodeTypes);
        if (names.length > 0) {
          onHighlight(names);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [query, nodeCount, edgeCount, nodeTypes, onHighlight],
  );

  const handleClear = useCallback(() => {
    setQuery("");
    setResponse(null);
    setError(null);
    onHighlight([]);
  }, [onHighlight]);

  return (
    <div className="space-y-2 p-4 border-t border-gray-700">
      {/* Stats summary */}
      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span>{nodeCount} nodes</span>
        <span>{edgeCount} edges</span>
        <span>{nodeTypes.length} types</span>
      </div>

      {/* Query input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask the graph..."
          className="flex-1 rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Send"
        >
          {loading ? (
            <svg
              className="w-4 h-4 animate-spin"
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
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          )}
        </button>
      </form>

      {/* Response */}
      {error && (
        <div className="bg-red-900/40 border border-red-700 rounded px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}

      {response && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 space-y-1">
          <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
            {response}
          </p>
          <button
            onClick={handleClear}
            className="text-xs text-gray-500 hover:text-gray-300"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
