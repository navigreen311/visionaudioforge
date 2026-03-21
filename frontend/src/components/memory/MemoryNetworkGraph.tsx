"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MemoryNode {
  id: string;
  content: string;
  category: string;
  importance: number;
  tags: string[];
  created_at: number;
}

interface SimNode extends MemoryNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  pinned: boolean;
}

interface GraphEdge {
  source: string;
  target: string;
  sharedTag: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_NODES = 50;

const CATEGORY_COLORS: Record<string, string> = {
  general: "#6b7280",
  vision: "#3b82f6",
  audio: "#8b5cf6",
  pipeline: "#22c55e",
  investigation: "#f97316",
  annotation: "#ec4899",
  agent: "#14b8a6",
  system: "#ef4444",
};

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] ?? CATEGORY_COLORS.general;
}

// ---------------------------------------------------------------------------
// Edge builder — connect nodes that share tags
// ---------------------------------------------------------------------------

function buildEdges(nodes: MemoryNode[]): GraphEdge[] {
  const edges: GraphEdge[] = [];
  const seen = new Set<string>();

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i];
      const b = nodes[j];
      const shared = a.tags.filter((t) => b.tags.includes(t));
      if (shared.length > 0) {
        const key = `${a.id}::${b.id}`;
        if (!seen.has(key)) {
          seen.add(key);
          edges.push({ source: a.id, target: b.id, sharedTag: shared[0] });
        }
      }
    }
  }
  return edges;
}

// ---------------------------------------------------------------------------
// Force-directed simulation
// ---------------------------------------------------------------------------

function initializePositions(
  nodes: MemoryNode[],
  width: number,
  height: number,
): SimNode[] {
  return nodes.map((n) => ({
    ...n,
    x: width / 2 + (Math.random() - 0.5) * 300,
    y: height / 2 + (Math.random() - 0.5) * 300,
    vx: 0,
    vy: 0,
    pinned: false,
  }));
}

function simulationStep(
  nodes: SimNode[],
  edges: GraphEdge[],
  width: number,
  height: number,
): void {
  const nodeMap = new Map<string, SimNode>();
  nodes.forEach((n) => nodeMap.set(n.id, n));

  const damping = 0.85;
  const repulsion = 3000;
  const attraction = 0.005;
  const idealLength = 120;
  const centerGravity = 0.01;
  const cx = width / 2;
  const cy = height / 2;

  // Repulsion between all node pairs
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i];
      const b = nodes[j];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = repulsion / (dist * dist);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      if (!a.pinned) {
        a.vx -= fx;
        a.vy -= fy;
      }
      if (!b.pinned) {
        b.vx += fx;
        b.vy += fy;
      }
    }
  }

  // Attraction along edges
  for (const edge of edges) {
    const source = nodeMap.get(edge.source);
    const target = nodeMap.get(edge.target);
    if (!source || !target) continue;
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const force = (dist - idealLength) * attraction;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    if (!source.pinned) {
      source.vx += fx;
      source.vy += fy;
    }
    if (!target.pinned) {
      target.vx -= fx;
      target.vy -= fy;
    }
  }

  // Center gravity + apply velocities
  const pad = 30;
  for (const node of nodes) {
    if (node.pinned) continue;
    node.vx += (cx - node.x) * centerGravity;
    node.vy += (cy - node.y) * centerGravity;
    node.vx *= damping;
    node.vy *= damping;
    node.x += node.vx;
    node.y += node.vy;
    node.x = Math.max(pad, Math.min(width - pad, node.x));
    node.y = Math.max(pad, Math.min(height - pad, node.y));
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface MemoryNetworkGraphProps {
  memories: MemoryNode[];
  width?: number;
  height?: number;
  onNodeSelect?: (memory: MemoryNode) => void;
}

export default function MemoryNetworkGraph({
  memories,
  width = 800,
  height = 600,
  onNodeSelect,
}: MemoryNetworkGraphProps) {
  const capped = memories.slice(0, MAX_NODES);
  const edges = buildEdges(capped);

  const simNodesRef = useRef<SimNode[]>([]);
  const animFrameRef = useRef<number>(0);
  const [, setTick] = useState(0);
  const iterRef = useRef(0);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const dragRef = useRef<{
    nodeId: string;
    offsetX: number;
    offsetY: number;
  } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Initialize positions when memories change
  useEffect(() => {
    simNodesRef.current = initializePositions(capped, width, height);
    iterRef.current = 0;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memories, width, height]);

  // Animation loop
  useEffect(() => {
    let running = true;
    const maxIter = 400;

    function step() {
      if (!running) return;
      if (iterRef.current < maxIter) {
        simulationStep(simNodesRef.current, edges, width, height);
        iterRef.current++;
        setTick((t) => t + 1);
      }
      animFrameRef.current = requestAnimationFrame(step);
    }

    animFrameRef.current = requestAnimationFrame(step);
    return () => {
      running = false;
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [edges, width, height]);

  // Reset layout
  const handleReset = useCallback(() => {
    simNodesRef.current = initializePositions(capped, width, height);
    iterRef.current = 0;
    setSelectedId(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memories, width, height]);

  // Drag helpers
  const getSvgPoint = useCallback(
    (clientX: number, clientY: number) => {
      const svg = svgRef.current;
      if (!svg) return { x: 0, y: 0 };
      const pt = svg.createSVGPoint();
      pt.x = clientX;
      pt.y = clientY;
      const ctm = svg.getScreenCTM();
      if (!ctm) return { x: 0, y: 0 };
      const svgPt = pt.matrixTransform(ctm.inverse());
      return { x: svgPt.x, y: svgPt.y };
    },
    [],
  );

  const handleMouseDown = useCallback(
    (nodeId: string, e: React.MouseEvent) => {
      e.preventDefault();
      const node = simNodesRef.current.find((n) => n.id === nodeId);
      if (!node) return;
      const svgPt = getSvgPoint(e.clientX, e.clientY);
      dragRef.current = {
        nodeId,
        offsetX: node.x - svgPt.x,
        offsetY: node.y - svgPt.y,
      };
      node.pinned = true;
    },
    [getSvgPoint],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragRef.current) return;
      const svgPt = getSvgPoint(e.clientX, e.clientY);
      const node = simNodesRef.current.find(
        (n) => n.id === dragRef.current?.nodeId,
      );
      if (!node) return;
      node.x = svgPt.x + dragRef.current.offsetX;
      node.y = svgPt.y + dragRef.current.offsetY;
      // Keep simulation alive while dragging
      iterRef.current = Math.min(iterRef.current, 350);
      setTick((t) => t + 1);
    },
    [getSvgPoint],
  );

  const handleMouseUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  const handleNodeClick = useCallback(
    (node: SimNode) => {
      if (dragRef.current) return; // Don't select while dragging
      setSelectedId(node.id);
      onNodeSelect?.(node);
    },
    [onNodeSelect],
  );

  // Build lookup
  const nodeMap = new Map<string, SimNode>();
  simNodesRef.current.forEach((n) => nodeMap.set(n.id, n));

  const selectedNode = selectedId ? nodeMap.get(selectedId) : null;

  // Unique categories present
  const presentCategories = Array.from(
    new Set(capped.map((m) => m.category)),
  );

  return (
    <div className="relative">
      {/* Toolbar */}
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs text-gray-400">
          {capped.length} nodes, {edges.length} edges
          {capped.length < memories.length &&
            ` (capped from ${memories.length})`}
        </span>
        <button
          onClick={handleReset}
          className="rounded bg-gray-700 px-3 py-1 text-xs text-gray-300 hover:bg-gray-600"
        >
          Reset Layout
        </button>
      </div>

      <div className="flex gap-4">
        {/* SVG Canvas */}
        <svg
          ref={svgRef}
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          className="rounded-lg border border-gray-700 bg-gray-900"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {/* Edges */}
          {edges.map((edge) => {
            const source = nodeMap.get(edge.source);
            const target = nodeMap.get(edge.target);
            if (!source || !target) return null;
            return (
              <line
                key={`${edge.source}-${edge.target}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke="#4b5563"
                strokeWidth={1}
                opacity={0.4}
              />
            );
          })}

          {/* Nodes */}
          {simNodesRef.current.map((node) => {
            const radius = Math.max(4, node.importance * 3 * 8);
            const color = getCategoryColor(node.category);
            const isHovered = hoveredId === node.id;
            const isSelected = selectedId === node.id;

            return (
              <g
                key={node.id}
                className="cursor-pointer"
                onMouseDown={(e) => handleMouseDown(node.id, e)}
                onClick={() => handleNodeClick(node)}
                onMouseEnter={() => setHoveredId(node.id)}
                onMouseLeave={() => setHoveredId(null)}
              >
                {/* Selection ring */}
                {isSelected && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={radius + 5}
                    fill="none"
                    stroke="#fbbf24"
                    strokeWidth={2}
                    opacity={0.8}
                  />
                )}
                {/* Pin indicator */}
                {node.pinned && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={radius + 3}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth={1}
                    strokeDasharray="3 2"
                    opacity={0.6}
                  />
                )}
                {/* Node circle */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={radius}
                  fill={color}
                  stroke={isHovered ? "#e5e7eb" : "#1f2937"}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  opacity={0.9}
                />
                {/* Label (only for larger or hovered nodes) */}
                {(radius > 10 || isHovered) && (
                  <text
                    x={node.x}
                    y={node.y + radius + 12}
                    fill="#d1d5db"
                    fontSize={9}
                    textAnchor="middle"
                    pointerEvents="none"
                  >
                    {node.content.length > 24
                      ? node.content.slice(0, 22) + "..."
                      : node.content}
                  </text>
                )}
              </g>
            );
          })}

          {/* Tooltip on hover */}
          {hoveredId && (() => {
            const node = nodeMap.get(hoveredId);
            if (!node) return null;
            const tx = Math.min(node.x + 15, width - 200);
            const ty = Math.max(node.y - 30, 20);
            return (
              <g pointerEvents="none">
                <rect
                  x={tx}
                  y={ty}
                  width={190}
                  height={58}
                  rx={6}
                  fill="#1f2937"
                  stroke="#374151"
                  strokeWidth={1}
                  opacity={0.95}
                />
                <text x={tx + 8} y={ty + 16} fill="#f3f4f6" fontSize={11}>
                  {node.content.slice(0, 28)}
                </text>
                <text x={tx + 8} y={ty + 32} fill="#9ca3af" fontSize={10}>
                  {node.category} | imp: {(node.importance * 100).toFixed(0)}%
                </text>
                <text x={tx + 8} y={ty + 48} fill="#6b7280" fontSize={9}>
                  tags: {node.tags.slice(0, 3).join(", ")}
                </text>
              </g>
            );
          })()}

          {/* Category legend */}
          <g transform={`translate(${width - 120}, 16)`}>
            {presentCategories.map((cat, i) => (
              <g key={cat} transform={`translate(0, ${i * 18})`}>
                <circle cx={6} cy={6} r={5} fill={getCategoryColor(cat)} />
                <text x={16} y={10} fill="#9ca3af" fontSize={10}>
                  {cat}
                </text>
              </g>
            ))}
          </g>
        </svg>

        {/* Detail panel */}
        {selectedNode && (
          <div className="w-64 shrink-0 rounded-lg border border-gray-700 bg-gray-800 p-4">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-200">
                Memory Detail
              </h3>
              <button
                onClick={() => setSelectedId(null)}
                className="text-gray-500 hover:text-gray-300"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M3 3l8 8M11 3l-8 8" />
                </svg>
              </button>
            </div>
            <p className="mb-2 text-sm text-gray-300">
              {selectedNode.content}
            </p>
            <div className="space-y-1 text-xs text-gray-400">
              <div>
                <span className="font-medium text-gray-300">Category:</span>{" "}
                {selectedNode.category}
              </div>
              <div>
                <span className="font-medium text-gray-300">Importance:</span>{" "}
                {(selectedNode.importance * 100).toFixed(0)}%
              </div>
              <div>
                <span className="font-medium text-gray-300">Tags:</span>{" "}
                {selectedNode.tags.join(", ") || "none"}
              </div>
              <div>
                <span className="font-medium text-gray-300">Created:</span>{" "}
                {new Date(
                  selectedNode.created_at * 1000,
                ).toLocaleDateString()}
              </div>
              <div>
                <span className="font-medium text-gray-300">Pinned:</span>{" "}
                {selectedNode.pinned ? "Yes" : "No"}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
