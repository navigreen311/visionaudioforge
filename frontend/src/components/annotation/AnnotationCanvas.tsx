"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import type { AnnotationTool } from "./ToolPalette";
import type { AnnotationItem } from "./AnnotationList";

interface DrawState {
  drawing: boolean;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  polygonPoints: [number, number][];
}

interface AnnotationCanvasProps {
  imageUrl: string | null;
  activeTool: AnnotationTool;
  annotations: AnnotationItem[];
  selectedId: string | null;
  activeLabel: string;
  onAnnotationCreate: (type: string, data: Record<string, unknown>) => void;
  onSelect: (id: string | null) => void;
}

const COLORS = [
  "#3b82f6", "#22c55e", "#a855f7", "#f97316", "#ef4444",
  "#06b6d4", "#eab308", "#ec4899", "#6366f1", "#14b8a6",
];

function labelColor(label: string): string {
  let hash = 0;
  for (let i = 0; i < label.length; i++) {
    hash = label.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

export default function AnnotationCanvas({
  imageUrl,
  activeTool,
  annotations,
  selectedId,
  activeLabel,
  onAnnotationCreate,
  onSelect,
}: AnnotationCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);

  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });

  const [drawState, setDrawState] = useState<DrawState>({
    drawing: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    polygonPoints: [],
  });

  // Load image
  useEffect(() => {
    if (!imageUrl) return;
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      imageRef.current = img;
      setImgSize({ w: img.naturalWidth, h: img.naturalHeight });
      setZoom(1);
      setPan({ x: 0, y: 0 });
    };
    img.src = imageUrl;
  }, [imageUrl]);

  // Convert screen coords to image coords
  const screenToImage = useCallback(
    (sx: number, sy: number): [number, number] => {
      const canvas = canvasRef.current;
      if (!canvas) return [0, 0];
      const rect = canvas.getBoundingClientRect();
      const x = (sx - rect.left - pan.x) / zoom;
      const y = (sy - rect.top - pan.y) / zoom;
      return [x, y];
    },
    [zoom, pan]
  );

  // Redraw main canvas
  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const container = containerRef.current;
    if (container) {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    // Draw image
    if (imageRef.current) {
      ctx.drawImage(imageRef.current, 0, 0);
    }

    // Draw existing annotations
    for (const ann of annotations) {
      const d = ann.data;
      const color = labelColor((d.label as string) || "default");
      const isSelected = ann.id === selectedId;
      ctx.strokeStyle = color;
      ctx.lineWidth = isSelected ? 3 / zoom : 2 / zoom;
      ctx.fillStyle = color + "33";

      switch (ann.annotation_type) {
        case "bbox": {
          const bx = (d.x as number) || 0;
          const by = (d.y as number) || 0;
          const bw = (d.width as number) || 0;
          const bh = (d.height as number) || 0;
          ctx.fillRect(bx, by, bw, bh);
          ctx.strokeRect(bx, by, bw, bh);
          // Label
          ctx.fillStyle = color;
          ctx.font = `${14 / zoom}px sans-serif`;
          ctx.fillText((d.label as string) || "", bx, by - 4 / zoom);
          break;
        }
        case "polygon": {
          const pts = (d.points as [number, number][]) || [];
          if (pts.length > 1) {
            ctx.beginPath();
            ctx.moveTo(pts[0][0], pts[0][1]);
            for (let i = 1; i < pts.length; i++) {
              ctx.lineTo(pts[i][0], pts[i][1]);
            }
            ctx.closePath();
            ctx.fillStyle = color + "33";
            ctx.fill();
            ctx.stroke();
          }
          // Draw vertices
          for (const pt of pts) {
            ctx.beginPath();
            ctx.arc(pt[0], pt[1], 4 / zoom, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
          }
          if (pts.length > 0) {
            ctx.fillStyle = color;
            ctx.font = `${14 / zoom}px sans-serif`;
            ctx.fillText((d.label as string) || "", pts[0][0], pts[0][1] - 6 / zoom);
          }
          break;
        }
        case "keypoint": {
          const kps = (d.points as { name: string; x: number; y: number }[]) || [];
          for (const kp of kps) {
            ctx.beginPath();
            ctx.arc(kp.x, kp.y, 6 / zoom, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 1.5 / zoom;
            ctx.stroke();
            ctx.fillStyle = color;
            ctx.font = `${11 / zoom}px sans-serif`;
            ctx.fillText(kp.name, kp.x + 8 / zoom, kp.y + 4 / zoom);
          }
          break;
        }
      }
    }

    ctx.restore();
  }, [annotations, selectedId, zoom, pan]);

  useEffect(() => {
    redraw();
  }, [redraw, imgSize]);

  // Draw overlay for in-progress drawing
  const redrawOverlay = useCallback(() => {
    const overlay = overlayRef.current;
    const octx = overlay?.getContext("2d");
    if (!overlay || !octx) return;

    const container = containerRef.current;
    if (container) {
      overlay.width = container.clientWidth;
      overlay.height = container.clientHeight;
    }
    octx.clearRect(0, 0, overlay.width, overlay.height);

    if (!drawState.drawing && drawState.polygonPoints.length === 0) return;

    octx.save();
    octx.translate(pan.x, pan.y);
    octx.scale(zoom, zoom);
    octx.strokeStyle = "#3b82f6";
    octx.lineWidth = 2 / zoom;
    octx.setLineDash([6 / zoom, 4 / zoom]);

    if (activeTool === "bbox" && drawState.drawing) {
      const x = Math.min(drawState.startX, drawState.currentX);
      const y = Math.min(drawState.startY, drawState.currentY);
      const w = Math.abs(drawState.currentX - drawState.startX);
      const h = Math.abs(drawState.currentY - drawState.startY);
      octx.strokeRect(x, y, w, h);
      octx.fillStyle = "#3b82f633";
      octx.fillRect(x, y, w, h);
    }

    if (activeTool === "polygon" && drawState.polygonPoints.length > 0) {
      octx.beginPath();
      const pts = drawState.polygonPoints;
      octx.moveTo(pts[0][0], pts[0][1]);
      for (let i = 1; i < pts.length; i++) {
        octx.lineTo(pts[i][0], pts[i][1]);
      }
      if (drawState.drawing) {
        octx.lineTo(drawState.currentX, drawState.currentY);
      }
      octx.stroke();
      // Draw vertices
      octx.setLineDash([]);
      for (const pt of pts) {
        octx.beginPath();
        octx.arc(pt[0], pt[1], 4 / zoom, 0, Math.PI * 2);
        octx.fillStyle = "#3b82f6";
        octx.fill();
      }
    }

    octx.restore();
  }, [drawState, activeTool, zoom, pan]);

  useEffect(() => {
    redrawOverlay();
  }, [redrawOverlay]);

  // Mouse handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && activeTool === "select" && e.shiftKey)) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      return;
    }

    if (activeTool === "select") {
      // Hit test - simplified: just deselect
      onSelect(null);
      return;
    }

    const [ix, iy] = screenToImage(e.clientX, e.clientY);

    if (activeTool === "bbox") {
      setDrawState((s) => ({ ...s, drawing: true, startX: ix, startY: iy, currentX: ix, currentY: iy }));
    } else if (activeTool === "polygon") {
      setDrawState((s) => ({
        ...s,
        drawing: true,
        polygonPoints: [...s.polygonPoints, [ix, iy]],
        currentX: ix,
        currentY: iy,
      }));
    } else if (activeTool === "keypoint") {
      onAnnotationCreate("keypoint", {
        points: [{ name: `kp_0`, x: ix, y: iy }],
        label: activeLabel,
      });
    } else if (activeTool === "label") {
      onAnnotationCreate("label", { label: activeLabel, confidence: 1.0 });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
      return;
    }
    if (!drawState.drawing) return;

    const [ix, iy] = screenToImage(e.clientX, e.clientY);
    setDrawState((s) => ({ ...s, currentX: ix, currentY: iy }));
  };

  const handleMouseUp = () => {
    if (isPanning) {
      setIsPanning(false);
      return;
    }
    if (!drawState.drawing) return;

    if (activeTool === "bbox") {
      const x = Math.min(drawState.startX, drawState.currentX);
      const y = Math.min(drawState.startY, drawState.currentY);
      const w = Math.abs(drawState.currentX - drawState.startX);
      const h = Math.abs(drawState.currentY - drawState.startY);
      if (w > 2 && h > 2) {
        onAnnotationCreate("bbox", { x, y, width: w, height: h, label: activeLabel });
      }
      setDrawState({ drawing: false, startX: 0, startY: 0, currentX: 0, currentY: 0, polygonPoints: [] });
    }
    // Polygon: mouse up doesn't finish — need double-click
  };

  const handleDoubleClick = () => {
    if (activeTool === "polygon" && drawState.polygonPoints.length >= 3) {
      onAnnotationCreate("polygon", {
        points: drawState.polygonPoints,
        label: activeLabel,
      });
      setDrawState({ drawing: false, startX: 0, startY: 0, currentX: 0, currentY: 0, polygonPoints: [] });
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((z) => Math.min(Math.max(z * delta, 0.1), 10));
  };

  // Reset polygon when tool changes
  useEffect(() => {
    setDrawState({ drawing: false, startX: 0, startY: 0, currentX: 0, currentY: 0, polygonPoints: [] });
  }, [activeTool]);

  const placeholder = !imageUrl;

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full min-h-[500px] bg-gray-900 rounded-lg overflow-hidden"
      onWheel={handleWheel}
    >
      {placeholder ? (
        <div className="absolute inset-0 flex items-center justify-center text-gray-400">
          <div className="text-center">
            <svg className="h-16 w-16 mx-auto mb-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p className="text-sm">Select an asset to annotate</p>
          </div>
        </div>
      ) : (
        <>
          <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full"
          />
          <canvas
            ref={overlayRef}
            className="absolute inset-0 w-full h-full"
            style={{ cursor: activeTool === "select" ? "default" : "crosshair" }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onDoubleClick={handleDoubleClick}
          />
        </>
      )}

      {/* Zoom indicator */}
      <div className="absolute bottom-3 right-3 bg-black/60 text-white text-xs px-2 py-1 rounded">
        {Math.round(zoom * 100)}%
      </div>
    </div>
  );
}
