"use client";

import { GraphNode, GraphEdge } from "./GraphCanvas";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface NodeDetailProps {
  node: GraphNode | null;
  edges: GraphEdge[];
  allNodes: GraphNode[];
  onClose?: () => void;
  onNavigate?: (nodeId: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NodeDetail({
  node,
  edges,
  allNodes,
  onClose,
  onNavigate,
}: NodeDetailProps) {
  if (!node) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm p-4">
        Click a node to view details
      </div>
    );
  }

  // Find connected edges
  const connectedEdges = edges.filter(
    (e) => e.source_id === node.id || e.target_id === node.id
  );

  // Resolve neighbor labels
  const nodeMap = new Map(allNodes.map((n) => [n.id, n]));

  const typeColorMap: Record<string, string> = {
    person: "bg-blue-500",
    object: "bg-green-500",
    location: "bg-orange-500",
    event: "bg-red-500",
    vehicle: "bg-purple-500",
    unknown: "bg-gray-500",
  };
  const badgeColor = typeColorMap[node.type] || typeColorMap.unknown;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-100">{node.label}</h3>
          <span
            className={`inline-block mt-1 px-2 py-0.5 rounded text-xs text-white ${badgeColor}`}
          >
            {node.type}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 text-lg"
            title="Close"
          >
            x
          </button>
        )}
      </div>

      {/* Properties */}
      {node.properties && Object.keys(node.properties).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2">Properties</h4>
          <div className="space-y-1">
            {Object.entries(node.properties).map(([key, value]) => (
              <div key={key} className="flex justify-between text-sm">
                <span className="text-gray-500">{key}</span>
                <span className="text-gray-300">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Relationships */}
      <div>
        <h4 className="text-sm font-medium text-gray-400 mb-2">
          Relationships ({connectedEdges.length})
        </h4>
        {connectedEdges.length === 0 ? (
          <p className="text-sm text-gray-600">No connections found</p>
        ) : (
          <div className="space-y-2">
            {connectedEdges.map((edge) => {
              const isOutgoing = edge.source_id === node.id;
              const otherId = isOutgoing ? edge.target_id : edge.source_id;
              const otherLabel = isOutgoing
                ? edge.target_label || nodeMap.get(otherId)?.label || otherId
                : edge.source_label || nodeMap.get(otherId)?.label || otherId;

              return (
                <div
                  key={edge.id}
                  className="flex items-center gap-2 text-sm bg-gray-800 rounded px-3 py-2 cursor-pointer hover:bg-gray-700"
                  onClick={() => onNavigate?.(otherId)}
                >
                  <span className="text-gray-400">
                    {isOutgoing ? "->" : "<-"}
                  </span>
                  <span className="text-blue-400 font-medium">{edge.relationship}</span>
                  <span className="text-gray-400">
                    {isOutgoing ? "->" : "<-"}
                  </span>
                  <span className="text-gray-200">{otherLabel}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Node ID */}
      <div className="text-xs text-gray-600 pt-2 border-t border-gray-700">
        ID: {node.id}
      </div>
    </div>
  );
}
