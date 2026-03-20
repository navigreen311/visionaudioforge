"use client";

import { useEffect, useRef, useCallback, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, unknown>;
  // Physics simulation fields
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphEdge {
  id: string;
  source_id: string;
  target_id: string;
  source_label?: string;
  target_label?: string;
  relationship: string;
  properties?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Color mapping by node type
// ---------------------------------------------------------------------------

const NODE_COLORS: Record<string, string> = {
  person: "#3b82f6",   // blue
  object: "#22c55e",   // green
  location: "#f97316", // orange
  event: "#ef4444",    // red
  vehicle: "#a855f7",  // purple
  unknown: "#6b7280",  // gray
};

function getNodeColor(type: string): string {
  return NODE_COLORS[type] || NODE_COLORS.unknown;
}

// ---------------------------------------------------------------------------
// Force-directed simulation
// ---------------------------------------------------------------------------

interface SimNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

function initializePositions(nodes: GraphNode[], width: number, height: number): SimNode[] {
  return nodes.map((n, i) => ({
    ...n,
    x: n.x ?? width / 2 + (Math.random() - 0.5) * 300,
    y: n.y ?? height / 2 + (Math.random() - 0.5) * 300,
    vx: 0,
    vy: 0,
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
      let dx = b.x - a.x;
      let dy = b.y - a.y;
      let dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = repulsion / (dist * dist);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx -= fx;
      a.vy -= fy;
      b.vx += fx;
      b.vy += fy;
    }
  }

  // Attraction along edges
  for (const edge of edges) {
    const source = nodeMap.get(edge.source_id);
    const target = nodeMap.get(edge.target_id);
    if (!source || !target) continue;
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const force = (dist - idealLength) * attraction;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    source.vx += fx;
    source.vy += fy;
    target.vx -= fx;
    target.vy -= fy;
  }

  // Center gravity
  for (const node of nodes) {
    node.vx += (cx - node.x) * centerGravity;
    node.vy += (cy - node.y) * centerGravity;
  }

  // Apply velocities with damping
  for (const node of nodes) {
    node.vx *= damping;
    node.vy *= damping;
    node.x += node.vx;
    node.y += node.vy;

    // Keep in bounds with padding
    const pad = 30;
    node.x = Math.max(pad, Math.min(width - pad, node.x));
    node.y = Math.max(pad, Math.min(height - pad, node.y));
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId?: string | null;
  highlightedNodeId?: string | null;
  onNodeClick?: (node: GraphNode) => void;
  width?: number;
  height?: number;
}

export default function GraphCanvas({
  nodes,
  edges,
  selectedNodeId,
  highlightedNodeId,
  onNodeClick,
  width = 800,
  height = 600,
}: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simNodesRef = useRef<SimNode[]>([]);
  const animFrameRef = useRef<number>(0);
  const [, setTick] = useState(0);
  const iterRef = useRef(0);

  // Initialize / update simulation nodes when props change
  useEffect(() => {
    simNodesRef.current = initializePositions(nodes, width, height);
    iterRef.current = 0;
  }, [nodes, width, height]);

  // Run simulation loop
  useEffect(() => {
    let running = true;
    const maxIter = 300;

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

  const nodeMap = new Map<string, SimNode>();
  simNodesRef.current.forEach((n) => nodeMap.set(n.id, n));

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      className="bg-gray-900 rounded-lg border border-gray-700"
      viewBox={`0 0 ${width} ${height}`}
    >
      {/* Edges */}
      {edges.map((edge) => {
        const source = nodeMap.get(edge.source_id);
        const target = nodeMap.get(edge.target_id);
        if (!source || !target) return null;
        const mx = (source.x + target.x) / 2;
        const my = (source.y + target.y) / 2;
        return (
          <g key={edge.id}>
            <line
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke="#4b5563"
              strokeWidth={1.5}
              opacity={0.6}
            />
            {edge.relationship && (
              <text
                x={mx}
                y={my - 6}
                fill="#9ca3af"
                fontSize={9}
                textAnchor="middle"
                pointerEvents="none"
              >
                {edge.relationship}
              </text>
            )}
          </g>
        );
      })}

      {/* Nodes */}
      {simNodesRef.current.map((node) => {
        const isSelected = node.id === selectedNodeId;
        const isHighlighted = node.id === highlightedNodeId;
        const radius = isSelected ? 18 : isHighlighted ? 16 : 12;
        const color = getNodeColor(node.type);

        return (
          <g
            key={node.id}
            onClick={() => onNodeClick?.(node)}
            className="cursor-pointer"
          >
            {/* Highlight ring */}
            {(isSelected || isHighlighted) && (
              <circle
                cx={node.x}
                cy={node.y}
                r={radius + 4}
                fill="none"
                stroke={isSelected ? "#fbbf24" : "#60a5fa"}
                strokeWidth={2}
                opacity={0.8}
              />
            )}
            <circle
              cx={node.x}
              cy={node.y}
              r={radius}
              fill={color}
              stroke="#1f2937"
              strokeWidth={2}
              opacity={0.9}
            />
            <text
              x={node.x}
              y={node.y + radius + 14}
              fill="#e5e7eb"
              fontSize={10}
              textAnchor="middle"
              pointerEvents="none"
            >
              {node.label.length > 20
                ? node.label.slice(0, 18) + "..."
                : node.label}
            </text>
          </g>
        );
      })}

      {/* Legend */}
      <g transform={`translate(${width - 130}, 20)`}>
        {Object.entries(NODE_COLORS)
          .filter(([k]) => k !== "unknown")
          .map(([type, color], i) => (
            <g key={type} transform={`translate(0, ${i * 18})`}>
              <circle cx={6} cy={6} r={5} fill={color} />
              <text x={16} y={10} fill="#9ca3af" fontSize={10}>
                {type}
              </text>
            </g>
          ))}
      </g>
    </svg>
  );
}
