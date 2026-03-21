'use client';

import { useRef, useCallback, useMemo } from 'react';
import type { GraphNode, GraphEdge } from './GraphCanvas';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Viewport {
  x: number;
  y: number;
  width: number;
  height: number;
  zoom: number;
}

interface GraphMinimapProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  viewport: Viewport;
  onPan: (x: number, y: number) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomFit: () => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAP_W = 120;
const MAP_H = 80;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GraphMinimap({
  nodes,
  edges,
  viewport,
  onPan,
  onZoomIn,
  onZoomOut,
  onZoomFit,
}: GraphMinimapProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Compute bounds from all nodes
  const bounds = useMemo(() => {
    if (nodes.length === 0) {
      return { minX: 0, minY: 0, maxX: 800, maxY: 600 };
    }
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const n of nodes) {
      const nx = n.x ?? 400;
      const ny = n.y ?? 300;
      if (nx < minX) minX = nx;
      if (ny < minY) minY = ny;
      if (nx > maxX) maxX = nx;
      if (ny > maxY) maxY = ny;
    }
    // Add padding
    const pad = 40;
    return {
      minX: minX - pad,
      minY: minY - pad,
      maxX: maxX + pad,
      maxY: maxY + pad,
    };
  }, [nodes]);

  const graphW = bounds.maxX - bounds.minX || 1;
  const graphH = bounds.maxY - bounds.minY || 1;

  // Scale to fit minimap
  const scale = Math.min(MAP_W / graphW, MAP_H / graphH);

  const toMapX = useCallback(
    (x: number) => (x - bounds.minX) * scale,
    [bounds.minX, scale],
  );
  const toMapY = useCallback(
    (y: number) => (y - bounds.minY) * scale,
    [bounds.minY, scale],
  );

  // Viewport rectangle in minimap coords
  const vpRect = useMemo(
    () => ({
      x: toMapX(viewport.x),
      y: toMapY(viewport.y),
      w: viewport.width * scale / viewport.zoom,
      h: viewport.height * scale / viewport.zoom,
    }),
    [viewport, scale, toMapX, toMapY],
  );

  // Node map for edge lookups
  const nodeMap = useMemo(
    () => new Map(nodes.map((n) => [n.id, n])),
    [nodes],
  );

  // Handle click on minimap to pan
  const handleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      // Convert back to graph coords
      const gx = mx / scale + bounds.minX;
      const gy = my / scale + bounds.minY;
      onPan(gx, gy);
    },
    [scale, bounds.minX, bounds.minY, onPan],
  );

  const zoomPercent = Math.round(viewport.zoom * 100);

  return (
    <div className="absolute bottom-4 right-4 flex flex-col items-end gap-2">
      {/* Zoom controls */}
      <div className="flex items-center gap-1 bg-gray-900/90 border border-gray-700 rounded px-2 py-1">
        <button
          type="button"
          onClick={onZoomOut}
          className="w-6 h-6 flex items-center justify-center text-gray-300 hover:text-white text-sm font-bold rounded hover:bg-gray-700"
          title="Zoom out"
        >
          -
        </button>
        <span className="text-xs text-gray-400 w-10 text-center tabular-nums">
          {zoomPercent}%
        </span>
        <button
          type="button"
          onClick={onZoomIn}
          className="w-6 h-6 flex items-center justify-center text-gray-300 hover:text-white text-sm font-bold rounded hover:bg-gray-700"
          title="Zoom in"
        >
          +
        </button>
        <div className="w-px h-4 bg-gray-700 mx-1" />
        <button
          type="button"
          onClick={onZoomFit}
          className="px-1.5 py-0.5 text-xs text-gray-400 hover:text-white rounded hover:bg-gray-700"
          title="Fit to view"
        >
          Fit
        </button>
      </div>

      {/* Minimap */}
      <div className="bg-gray-900/90 border border-gray-700 rounded p-1">
        <svg
          ref={svgRef}
          width={MAP_W}
          height={MAP_H}
          className="cursor-crosshair"
          onClick={handleClick}
        >
          {/* Background */}
          <rect width={MAP_W} height={MAP_H} fill="#111827" rx={2} />

          {/* Edges */}
          {edges.map((edge) => {
            const source = nodeMap.get(edge.source_id);
            const target = nodeMap.get(edge.target_id);
            if (!source || !target) return null;
            return (
              <line
                key={edge.id}
                x1={toMapX(source.x ?? 0)}
                y1={toMapY(source.y ?? 0)}
                x2={toMapX(target.x ?? 0)}
                y2={toMapY(target.y ?? 0)}
                stroke="#374151"
                strokeWidth={0.5}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => (
            <circle
              key={node.id}
              cx={toMapX(node.x ?? 0)}
              cy={toMapY(node.y ?? 0)}
              r={1.5}
              fill="#60a5fa"
            />
          ))}

          {/* Viewport rectangle */}
          <rect
            x={vpRect.x}
            y={vpRect.y}
            width={Math.max(vpRect.w, 8)}
            height={Math.max(vpRect.h, 5)}
            fill="none"
            stroke="#fbbf24"
            strokeWidth={1}
            rx={1}
            opacity={0.8}
          />
        </svg>
      </div>
    </div>
  );
}
