"use client";

import { useState, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface NodeProperties {
  [key: string]: string | number | boolean;
}

interface NodeDetailData {
  id: string;
  label: string;
  type: string;
  properties: NodeProperties;
  created_at: string;
  updated_at: string;
}

interface NodeEdge {
  id: string;
  relationship: string;
  direction: "outgoing" | "incoming";
  connected_node_id: string;
  connected_node_label: string;
  connected_node_type: string;
}

interface LinkedAsset {
  id: string;
  filename: string;
  thumbnail_url: string | null;
  media_type: string;
}

interface NodeDetailPanelProps {
  nodeId: string | null;
  onNodeFocus: (id: string) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TYPE_BADGE_COLORS: Record<string, string> = {
  person: "bg-blue-500",
  object: "bg-green-500",
  location: "bg-orange-500",
  event: "bg-red-500",
  vehicle: "bg-purple-500",
};

function getBadgeColor(type: string): string {
  return TYPE_BADGE_COLORS[type.toLowerCase()] || "bg-gray-500";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NodeDetailPanel({
  nodeId,
  onNodeFocus,
}: NodeDetailPanelProps) {
  const [node, setNode] = useState<NodeDetailData | null>(null);
  const [edges, setEdges] = useState<NodeEdge[]>([]);
  const [assets, setAssets] = useState<LinkedAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNodeDetail = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);

    try {
      const [nodeRes, edgesRes, assetsRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/knowledge-graph/nodes/${id}`),
        fetch(`${API_BASE}/api/knowledge-graph/nodes/${id}/edges`),
        fetch(`${API_BASE}/api/knowledge-graph/nodes/${id}/assets`),
      ]);

      if (nodeRes.status === "fulfilled" && nodeRes.value.ok) {
        const nodeData = await nodeRes.value.json() as NodeDetailData;
        setNode(nodeData);
      } else {
        setError("Failed to load node details");
        return;
      }

      if (edgesRes.status === "fulfilled" && edgesRes.value.ok) {
        const edgesData = await edgesRes.value.json() as { edges: NodeEdge[] };
        setEdges(edgesData.edges ?? []);
      } else {
        setEdges([]);
      }

      if (assetsRes.status === "fulfilled" && assetsRes.value.ok) {
        const assetsData = await assetsRes.value.json() as { assets: LinkedAsset[] };
        setAssets(assetsData.assets ?? []);
      } else {
        setAssets([]);
      }
    } catch {
      setError("Network error loading node details");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (nodeId) {
      fetchNodeDetail(nodeId);
    } else {
      setNode(null);
      setEdges([]);
      setAssets([]);
      setError(null);
    }
  }, [nodeId, fetchNodeDetail]);

  // -- Empty state --
  if (!nodeId) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-500 p-6 gap-3">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-10 w-10 text-gray-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z"
          />
        </svg>
        <span className="text-sm text-center">Click a node to view details</span>
      </div>
    );
  }

  // -- Loading state --
  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400 text-sm">
        <span className="animate-pulse">Loading...</span>
      </div>
    );
  }

  // -- Error state --
  if (error || !node) {
    return (
      <div className="p-4 text-red-400 text-sm">
        {error || "Node not found"}
      </div>
    );
  }

  const propertyEntries = Object.entries(node.properties ?? {});

  return (
    <div className="h-full overflow-y-auto p-4 space-y-5">
      {/* ---- Header ---- */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`inline-block px-2 py-0.5 rounded text-xs font-medium text-white capitalize ${getBadgeColor(node.type)}`}
            >
              {node.type}
            </span>
          </div>
          <h3 className="text-lg font-bold text-gray-100 truncate">
            {node.label}
          </h3>
        </div>
        <div className="flex items-center gap-1 ml-2 flex-shrink-0">
          <button
            className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
            title="Edit node"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
          </button>
          <button
            className="p-1.5 rounded hover:bg-red-900/50 text-gray-400 hover:text-red-400 transition-colors"
            title="Delete node"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* ---- Properties ---- */}
      {propertyEntries.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
            Properties
          </h4>
          <div className="space-y-1 bg-gray-800/50 rounded-lg p-3">
            {propertyEntries.map(([key, value]) => (
              <div key={key} className="flex justify-between text-sm gap-2">
                <span className="text-gray-400 truncate">{key}</span>
                <span className="text-gray-200 text-right truncate">
                  {String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---- Connected Edges ---- */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
          Connections ({edges.length})
        </h4>
        {edges.length === 0 ? (
          <p className="text-sm text-gray-600">No connections</p>
        ) : (
          <div className="space-y-1.5">
            {edges.map((edge) => {
              const isOutgoing = edge.direction === "outgoing";
              return (
                <button
                  key={edge.id}
                  className="w-full flex items-center gap-2 text-sm bg-gray-800 rounded-lg px-3 py-2 hover:bg-gray-700 transition-colors text-left"
                  onClick={() => onNodeFocus(edge.connected_node_id)}
                >
                  <span className="text-gray-500 flex-shrink-0">
                    {isOutgoing ? "\u2192" : "\u2190"}
                  </span>
                  <span className="text-blue-400 font-medium truncate">
                    {edge.relationship}
                  </span>
                  <span className="text-gray-500 flex-shrink-0">
                    {isOutgoing ? "\u2192" : "\u2190"}
                  </span>
                  <span className="text-gray-200 truncate">
                    {edge.connected_node_label}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ---- Linked Assets ---- */}
      {assets.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
            Linked Assets ({assets.length})
          </h4>
          <div className="space-y-2">
            {assets.map((asset) => (
              <div
                key={asset.id}
                className="flex items-center gap-3 bg-gray-800/50 rounded-lg p-2"
              >
                {asset.thumbnail_url ? (
                  <img
                    src={asset.thumbnail_url}
                    alt={asset.filename}
                    className="w-12 h-12 rounded object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="w-12 h-12 rounded bg-gray-700 flex items-center justify-center flex-shrink-0">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-5 w-5 text-gray-500"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={1.5}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-200 truncate">
                    {asset.filename}
                  </p>
                  <p className="text-xs text-gray-500">{asset.media_type}</p>
                </div>
                <button
                  className="text-xs text-blue-400 hover:text-blue-300 px-2 py-1 rounded hover:bg-gray-700 transition-colors flex-shrink-0"
                  title="Open asset"
                >
                  Open
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---- Timestamps ---- */}
      <div className="pt-3 border-t border-gray-700 space-y-1">
        <div className="flex justify-between text-xs text-gray-600">
          <span>Created</span>
          <span>{new Date(node.created_at).toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-xs text-gray-600">
          <span>Updated</span>
          <span>{new Date(node.updated_at).toLocaleString()}</span>
        </div>
        <div className="text-xs text-gray-700 pt-1">
          ID: {node.id}
        </div>
      </div>
    </div>
  );
}
