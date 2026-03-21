"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import GraphCanvas, {
  GraphNode,
  GraphEdge,
} from "@/components/knowledge-graph/GraphCanvas";
import NodeDetailPanel from "@/components/knowledge-graph/NodeDetailPanel";
import GraphFilters, {
  GraphFilterState,
} from "@/components/knowledge-graph/GraphFilters";

// ---------------------------------------------------------------------------
// Dynamic imports for components from other agents (lazy-loaded)
// ---------------------------------------------------------------------------

const GraphSearch = dynamic(
  () => import("@/components/knowledge-graph/GraphSearch"),
  { ssr: false, loading: () => <div className="h-8 bg-gray-800 rounded animate-pulse" /> }
);

const AddEntityModal = dynamic(
  () => import("@/components/knowledge-graph/AddEntityModal"),
  { ssr: false }
);

const AddRelationshipModal = dynamic(
  () => import("@/components/knowledge-graph/AddRelationshipModal"),
  { ssr: false }
);

const PathFinder = dynamic(
  () => import("@/components/knowledge-graph/PathFinder"),
  { ssr: false }
);

const GraphToolbar = dynamic(
  () => import("@/components/knowledge-graph/GraphToolbar"),
  { ssr: false, loading: () => <div className="h-10 bg-gray-800 rounded animate-pulse" /> }
);

const GraphMinimap = dynamic(
  () => import("@/components/knowledge-graph/GraphMinimap"),
  { ssr: false }
);

const ExtractFromAsset = dynamic(
  () => import("@/components/knowledge-graph/ExtractFromAsset"),
  { ssr: false }
);

const GraphExport = dynamic(
  () => import("@/components/knowledge-graph/GraphExport"),
  { ssr: false }
);

const CopilotGraphQuery = dynamic(
  () => import("@/components/knowledge-graph/CopilotGraphQuery"),
  { ssr: false }
);

// ---------------------------------------------------------------------------
// Feature flags — set to true once the corresponding component is available
// ---------------------------------------------------------------------------

const FEATURES = {
  graphSearch: false,
  addEntity: false,
  addRelationship: false,
  pathFinder: false,
  graphToolbar: false,
  graphMinimap: false,
  extractFromAsset: false,
  graphExport: false,
  copilotGraphQuery: false,
} as const;

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchGraphContext(
  query: string,
  workspaceId: string
): Promise<{ nodes: GraphNode[]; edges: GraphEdge[]; context_text: string }> {
  const res = await fetch(`${API_BASE}/api/knowledge-graph/rag/context`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, workspace_id: workspaceId }),
  });
  if (!res.ok) throw new Error(`Failed to fetch graph context: ${res.status}`);
  return res.json();
}

async function fetchNLQuery(
  query: string,
  workspaceId: string
): Promise<{ parsed: Record<string, unknown>; results: unknown[]; query_type: string }> {
  const res = await fetch(`${API_BASE}/api/knowledge-graph/nl-query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, workspace_id: workspaceId }),
  });
  if (!res.ok) throw new Error(`Failed to query graph: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Demo data (used when no backend is connected)
// ---------------------------------------------------------------------------

function getDemoData(): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [
    { id: "p1", label: "John Smith", type: "person", properties: { role: "suspect", age: "34" } },
    { id: "p2", label: "Jane Doe", type: "person", properties: { role: "witness" } },
    { id: "p3", label: "Officer Lee", type: "person", properties: { role: "investigator" } },
    { id: "l1", label: "Main Street", type: "location", properties: { district: "downtown" } },
    { id: "l2", label: "Warehouse 5", type: "location", properties: { district: "industrial" } },
    { id: "v1", label: "Red Sedan", type: "vehicle", properties: { plate: "ABC-1234", color: "red" } },
    { id: "v2", label: "White Van", type: "vehicle", properties: { plate: "XYZ-5678", color: "white" } },
    { id: "o1", label: "Backpack", type: "object", properties: { color: "black" } },
    { id: "e1", label: "Incident #42", type: "event", properties: { time: "2025-01-15 10:30", severity: "high" } },
    { id: "e2", label: "Traffic Stop", type: "event", properties: { time: "2025-01-15 11:00" } },
  ];

  const edges: GraphEdge[] = [
    { id: "e-1", source_id: "p1", target_id: "l1", source_label: "John Smith", target_label: "Main Street", relationship: "was seen at" },
    { id: "e-2", source_id: "p1", target_id: "v1", source_label: "John Smith", target_label: "Red Sedan", relationship: "drove" },
    { id: "e-3", source_id: "p2", target_id: "l1", source_label: "Jane Doe", target_label: "Main Street", relationship: "witnessed at" },
    { id: "e-4", source_id: "p1", target_id: "o1", source_label: "John Smith", target_label: "Backpack", relationship: "carried" },
    { id: "e-5", source_id: "v1", target_id: "l2", source_label: "Red Sedan", target_label: "Warehouse 5", relationship: "parked at" },
    { id: "e-6", source_id: "p3", target_id: "e1", source_label: "Officer Lee", target_label: "Incident #42", relationship: "responded to" },
    { id: "e-7", source_id: "e1", target_id: "l1", source_label: "Incident #42", target_label: "Main Street", relationship: "occurred at" },
    { id: "e-8", source_id: "v2", target_id: "l2", source_label: "White Van", target_label: "Warehouse 5", relationship: "spotted near" },
    { id: "e-9", source_id: "p3", target_id: "e2", source_label: "Officer Lee", target_label: "Traffic Stop", relationship: "conducted" },
    { id: "e-10", source_id: "e2", target_id: "v1", source_label: "Traffic Stop", target_label: "Red Sedan", relationship: "involved" },
  ];

  return { nodes, edges };
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

const ALL_NODE_TYPES = ["person", "object", "location", "event", "vehicle"];

export default function KnowledgeGraphPage() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nlAnswer, setNlAnswer] = useState<string | null>(null);

  // Modal states for dynamic components
  const [showAddEntity, setShowAddEntity] = useState(false);
  const [showAddRelationship, setShowAddRelationship] = useState(false);
  const [showPathFinder, setShowPathFinder] = useState(false);
  const [showExtractFromAsset, setShowExtractFromAsset] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [showCopilot, setShowCopilot] = useState(false);

  // Filters
  const availableEdgeTypes = useMemo(() => {
    const types = new Set(edges.map((e) => e.relationship));
    return Array.from(types).sort();
  }, [edges]);

  const [filters, setFilters] = useState<GraphFilterState>({
    nodeTypes: new Set(ALL_NODE_TYPES),
    edgeTypes: new Set<string>(),
    searchTerm: "",
    timeRange: null,
  });

  // Sync edge filter defaults when edges change
  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      edgeTypes: new Set(availableEdgeTypes),
    }));
  }, [availableEdgeTypes]);

  // Load demo data on mount
  useEffect(() => {
    const demo = getDemoData();
    setNodes(demo.nodes);
    setEdges(demo.edges);
  }, []);

  // Search handler: try backend first, fall back to local filter
  const handleSearch = useCallback(
    async (term: string) => {
      setFilters((prev) => ({ ...prev, searchTerm: term }));
      setNlAnswer(null);

      if (!term.trim()) {
        setHighlightedNodeId(null);
        return;
      }

      // Try fetching from backend
      setLoading(true);
      setError(null);
      try {
        const workspaceId = "00000000-0000-0000-0000-000000000001";
        const contextData = await fetchGraphContext(term, workspaceId);

        if (contextData.nodes.length > 0) {
          setNodes(contextData.nodes);
          setEdges(contextData.edges);
          setHighlightedNodeId(contextData.nodes[0]?.id || null);
        } else {
          // Also try NL query for an answer
          const nlResult = await fetchNLQuery(term, workspaceId);
          if (nlResult.results?.length > 0) {
            setNlAnswer(JSON.stringify(nlResult, null, 2));
          }
        }
      } catch {
        // Backend unavailable — filter locally
        const termLower = term.toLowerCase();
        const match = nodes.find((n) =>
          n.label.toLowerCase().includes(termLower)
        );
        if (match) {
          setHighlightedNodeId(match.id);
        } else {
          setHighlightedNodeId(null);
        }
      } finally {
        setLoading(false);
      }
    },
    [nodes]
  );

  // Apply filters
  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => filters.nodeTypes.has(n.type));
  }, [nodes, filters.nodeTypes]);

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return edges.filter(
      (e) =>
        nodeIds.has(e.source_id) &&
        nodeIds.has(e.target_id) &&
        filters.edgeTypes.has(e.relationship)
    );
  }, [edges, filteredNodes, filters.edgeTypes]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNodeId(node.id);
    setHighlightedNodeId(node.id);
  }, []);

  const handleNodeFocus = useCallback(
    (nodeId: string) => {
      setSelectedNodeId(nodeId);
      setHighlightedNodeId(nodeId);
    },
    []
  );

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white">
        <h1 className="text-xl font-bold text-gray-900">Knowledge Graph</h1>
        <div className="flex items-center gap-3 text-sm text-gray-500">
          {FEATURES.addEntity && (
            <button
              className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-xs hover:bg-blue-700"
              onClick={() => setShowAddEntity(true)}
            >
              + Entity
            </button>
          )}
          {FEATURES.addRelationship && (
            <button
              className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs hover:bg-indigo-700"
              onClick={() => setShowAddRelationship(true)}
            >
              + Relationship
            </button>
          )}
          {FEATURES.extractFromAsset && (
            <button
              className="px-3 py-1.5 bg-green-600 text-white rounded-md text-xs hover:bg-green-700"
              onClick={() => setShowExtractFromAsset(true)}
            >
              Extract
            </button>
          )}
          {FEATURES.graphExport && (
            <button
              className="px-3 py-1.5 bg-gray-600 text-white rounded-md text-xs hover:bg-gray-700"
              onClick={() => setShowExport(true)}
            >
              Export
            </button>
          )}
          {FEATURES.copilotGraphQuery && (
            <button
              className="px-3 py-1.5 bg-purple-600 text-white rounded-md text-xs hover:bg-purple-700"
              onClick={() => setShowCopilot(true)}
            >
              Copilot
            </button>
          )}
          <span>{filteredNodes.length} nodes</span>
          <span>{filteredEdges.length} edges</span>
          {loading && (
            <span className="text-blue-500 animate-pulse">Loading...</span>
          )}
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-2 p-2 rounded bg-red-50 text-red-700 text-sm">
          {error}
        </div>
      )}

      {nlAnswer && (
        <div className="mx-6 mt-2 p-3 rounded bg-blue-50 text-blue-800 text-sm whitespace-pre-wrap max-h-32 overflow-y-auto">
          {nlAnswer}
        </div>
      )}

      {/* Toolbar area */}
      {FEATURES.graphToolbar && (
        <div className="px-6 py-2 border-b border-gray-200 bg-white">
          <GraphToolbar />
        </div>
      )}

      {/* Main layout: left panel | center graph | right panel */}
      <div className="flex flex-1 min-h-0">
        {/* Left panel: search + filters */}
        <div className="w-64 border-r border-gray-200 bg-gray-900 overflow-y-auto flex-shrink-0">
          {FEATURES.graphSearch && (
            <div className="p-3 border-b border-gray-700">
              <GraphSearch />
            </div>
          )}
          <GraphFilters
            availableNodeTypes={ALL_NODE_TYPES}
            availableEdgeTypes={availableEdgeTypes}
            filters={filters}
            onFiltersChange={setFilters}
            onSearch={handleSearch}
          />
          {FEATURES.pathFinder && (
            <div className="p-3 border-t border-gray-700">
              <button
                className="w-full text-xs text-gray-400 hover:text-gray-200 py-2"
                onClick={() => setShowPathFinder(true)}
              >
                Find Path Between Nodes
              </button>
            </div>
          )}
        </div>

        {/* Center: graph canvas */}
        <div className="flex-1 relative flex items-center justify-center bg-gray-950 overflow-hidden p-4">
          <GraphCanvas
            nodes={filteredNodes}
            edges={filteredEdges}
            selectedNodeId={selectedNodeId}
            highlightedNodeId={highlightedNodeId}
            onNodeClick={handleNodeClick}
            width={900}
            height={600}
          />
          {FEATURES.graphMinimap && (
            <div className="absolute bottom-4 right-4">
              <GraphMinimap />
            </div>
          )}
        </div>

        {/* Right panel: node detail */}
        <div className="w-80 border-l border-gray-200 bg-gray-900 overflow-y-auto flex-shrink-0">
          <NodeDetailPanel
            nodeId={selectedNodeId}
            onNodeFocus={handleNodeFocus}
          />
        </div>
      </div>

      {/* Dynamic modals (rendered only when feature flags are on) */}
      {FEATURES.addEntity && showAddEntity && (
        <AddEntityModal />
      )}
      {FEATURES.addRelationship && showAddRelationship && (
        <AddRelationshipModal />
      )}
      {FEATURES.pathFinder && showPathFinder && (
        <PathFinder />
      )}
      {FEATURES.extractFromAsset && showExtractFromAsset && (
        <ExtractFromAsset />
      )}
      {FEATURES.graphExport && showExport && (
        <GraphExport />
      )}
      {FEATURES.copilotGraphQuery && showCopilot && (
        <CopilotGraphQuery />
      )}
    </div>
  );
}
