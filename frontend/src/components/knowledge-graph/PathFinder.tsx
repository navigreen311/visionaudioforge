'use client';

import { API_BASE_URL } from "@/lib/api";

import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import type { GraphNode, GraphEdge } from './GraphCanvas';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PathHighlight {
  nodeIds: Set<string>;
  edgeIds: Set<string>;
}

interface PathResult {
  path: string[];
  labels: string[];
  hops: number;
}

interface PathFinderProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onHighlightPath: (highlight: PathHighlight) => void;
  onClear: () => void;
}

// ---------------------------------------------------------------------------
// Searchable selector dropdown
// ---------------------------------------------------------------------------

interface NodeSelectorProps {
  label: string;
  nodes: GraphNode[];
  value: string | null;
  onChange: (nodeId: string | null) => void;
}

function NodeSelector({ label, nodes, value, onChange }: NodeSelectorProps) {
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    if (!search.trim()) return nodes;
    const term = search.toLowerCase();
    return nodes.filter(
      (n) =>
        n.label.toLowerCase().includes(term) ||
        n.type.toLowerCase().includes(term),
    );
  }, [nodes, search]);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === value) ?? null,
    [nodes, value],
  );

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={containerRef} className="relative flex-1 min-w-[160px]">
      <span className="text-xs text-gray-400 mb-0.5 block">{label}</span>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full text-left rounded bg-gray-800 border border-gray-600 px-3 py-1.5 text-sm text-gray-200 hover:border-gray-500 focus:outline-none focus:border-amber-500 truncate"
      >
        {selectedNode ? selectedNode.label : 'Select node...'}
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded bg-gray-800 border border-gray-600 shadow-lg max-h-48 overflow-hidden flex flex-col">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search nodes..."
            className="px-3 py-1.5 text-sm bg-gray-700 text-gray-200 border-b border-gray-600 focus:outline-none"
            autoFocus
          />
          <div className="overflow-y-auto flex-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500">
                No matching nodes
              </div>
            ) : (
              filtered.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => {
                    onChange(n.id);
                    setOpen(false);
                    setSearch('');
                  }}
                  className={`w-full text-left px-3 py-1.5 text-sm hover:bg-gray-700 flex items-center gap-2 ${
                    n.id === value ? 'bg-gray-700 text-amber-400' : 'text-gray-200'
                  }`}
                >
                  <span className="text-xs text-gray-500">[{n.type}]</span>
                  <span className="truncate">{n.label}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PathFinder Component
// ---------------------------------------------------------------------------

const API_BASE = API_BASE_URL;

export default function PathFinder({
  nodes,
  edges,
  onHighlightPath,
  onClear,
}: PathFinderProps) {
  const [fromId, setFromId] = useState<string | null>(null);
  const [toId, setToId] = useState<string | null>(null);
  const [pathResult, setPathResult] = useState<PathResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nodeMap = useMemo(
    () => new Map(nodes.map((n) => [n.id, n])),
    [nodes],
  );

  const findPath = useCallback(async () => {
    if (!fromId || !toId) return;
    if (fromId === toId) {
      setError('From and To nodes must be different');
      return;
    }

    setLoading(true);
    setError(null);
    setPathResult(null);

    try {
      const res = await fetch(
        `${API_BASE}/api/knowledge-graph/path?from=${encodeURIComponent(fromId)}&to=${encodeURIComponent(toId)}`,
      );
      if (!res.ok) throw new Error(`Path query failed: ${res.status}`);
      const data: { path: string[]; hops: number } = await res.json();

      // Resolve labels
      const labels = data.path.map(
        (id) => nodeMap.get(id)?.label ?? id,
      );

      const result: PathResult = {
        path: data.path,
        labels,
        hops: data.hops,
      };
      setPathResult(result);

      // Build highlight sets
      const pathNodeIds = new Set(data.path);
      const pathEdgeIds = new Set<string>();

      for (let i = 0; i < data.path.length - 1; i++) {
        const a = data.path[i];
        const b = data.path[i + 1];
        const edge = edges.find(
          (e) =>
            (e.source_id === a && e.target_id === b) ||
            (e.source_id === b && e.target_id === a),
        );
        if (edge) pathEdgeIds.add(edge.id);
      }

      onHighlightPath({ nodeIds: pathNodeIds, edgeIds: pathEdgeIds });
    } catch {
      // Fallback: local BFS
      const adjList = new Map<string, { neighborId: string; edgeId: string }[]>();
      for (const n of nodes) {
        adjList.set(n.id, []);
      }
      for (const e of edges) {
        adjList.get(e.source_id)?.push({ neighborId: e.target_id, edgeId: e.id });
        adjList.get(e.target_id)?.push({ neighborId: e.source_id, edgeId: e.id });
      }

      // BFS
      const visited = new Set<string>();
      const parent = new Map<string, { nodeId: string; edgeId: string }>();
      const queue: string[] = [fromId];
      visited.add(fromId);
      let found = false;

      while (queue.length > 0 && !found) {
        const current = queue.shift()!;
        const neighbors = adjList.get(current) ?? [];
        for (const { neighborId, edgeId } of neighbors) {
          if (!visited.has(neighborId)) {
            visited.add(neighborId);
            parent.set(neighborId, { nodeId: current, edgeId });
            if (neighborId === toId) {
              found = true;
              break;
            }
            queue.push(neighborId);
          }
        }
      }

      if (!found) {
        setError('No path found between these nodes');
        return;
      }

      // Reconstruct path
      const pathIds: string[] = [];
      const pathEdgeIds = new Set<string>();
      let cur = toId;
      while (cur !== fromId) {
        pathIds.unshift(cur);
        const p = parent.get(cur);
        if (!p) break;
        pathEdgeIds.add(p.edgeId);
        cur = p.nodeId;
      }
      pathIds.unshift(fromId);

      const labels = pathIds.map((id) => nodeMap.get(id)?.label ?? id);
      const result: PathResult = {
        path: pathIds,
        labels,
        hops: pathIds.length - 1,
      };
      setPathResult(result);
      onHighlightPath({ nodeIds: new Set(pathIds), edgeIds: pathEdgeIds });
    } finally {
      setLoading(false);
    }
  }, [fromId, toId, nodes, edges, nodeMap, onHighlightPath]);

  const clearPath = useCallback(() => {
    setPathResult(null);
    setError(null);
    setFromId(null);
    setToId(null);
    onClear();
  }, [onClear]);

  return (
    <div className="bg-gray-900 border-b border-gray-700 px-4 py-3 space-y-2">
      <div className="flex items-end gap-3 flex-wrap">
        <NodeSelector label="From" nodes={nodes} value={fromId} onChange={setFromId} />
        <NodeSelector label="To" nodes={nodes} value={toId} onChange={setToId} />

        <button
          type="button"
          onClick={findPath}
          disabled={!fromId || !toId || loading}
          className="px-4 py-1.5 rounded bg-amber-600 text-white text-sm font-medium hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          {loading ? 'Searching...' : 'Find Shortest Path'}
        </button>

        {pathResult && (
          <button
            type="button"
            onClick={clearPath}
            className="px-3 py-1.5 rounded border border-gray-600 text-gray-400 text-sm hover:bg-gray-800 hover:text-gray-200 whitespace-nowrap"
          >
            Clear path
          </button>
        )}
      </div>

      {error && (
        <div className="text-sm text-red-400">{error}</div>
      )}

      {pathResult && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-400">Path:</span>
          {pathResult.labels.map((label, i) => (
            <span key={pathResult.path[i]} className="flex items-center gap-1">
              {i > 0 && <span className="text-gray-600">&rarr;</span>}
              <span className="text-amber-400 font-medium">{label}</span>
            </span>
          ))}
          <span className="text-gray-500 ml-2">
            ({pathResult.hops} {pathResult.hops === 1 ? 'hop' : 'hops'})
          </span>
        </div>
      )}
    </div>
  );
}
