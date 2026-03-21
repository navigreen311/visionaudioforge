"use client";

import { useState, useCallback, type RefObject } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GraphExportProps {
  graphRef: RefObject<SVGSVGElement | HTMLCanvasElement | null>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function svgToPng(svgEl: SVGSVGElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const serializer = new XMLSerializer();
    const svgStr = serializer.serializeToString(svgEl);
    const svgBlob = new Blob([svgStr], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);

    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = svgEl.width.baseVal.value || 800;
      canvas.height = svgEl.height.baseVal.value || 600;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("Could not get 2d context"));
        return;
      }
      ctx.drawImage(img, 0, 0);
      canvas.toBlob((blob) => {
        URL.revokeObjectURL(url);
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error("Canvas toBlob returned null"));
        }
      }, "image/png");
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Failed to load SVG as image"));
    };
    img.src = url;
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GraphExport({ graphRef }: GraphExportProps) {
  const [open, setOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleExportPng = useCallback(async () => {
    setExporting(true);
    try {
      const el = graphRef.current;
      if (!el) return;

      if (el instanceof HTMLCanvasElement) {
        // Canvas element — use toDataURL directly
        const dataUrl = el.toDataURL("image/png");
        const res = await fetch(dataUrl);
        const blob = await res.blob();
        downloadBlob(blob, "knowledge-graph.png");
      } else {
        // SVG element — serialize and rasterize
        const blob = await svgToPng(el);
        downloadBlob(blob, "knowledge-graph.png");
      }
    } catch (err) {
      console.error("PNG export failed:", err);
    } finally {
      setExporting(false);
      setOpen(false);
    }
  }, [graphRef]);

  const handleExportJson = useCallback(async () => {
    setExporting(true);
    try {
      const res = await fetch("/api/knowledge-graph/export?format=json");
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      downloadBlob(blob, "knowledge-graph.json");
    } catch (err) {
      console.error("JSON export failed:", err);
    } finally {
      setExporting(false);
      setOpen(false);
    }
  }, []);

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-gray-700 border border-gray-600 text-sm text-gray-200 hover:bg-gray-600"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        Export
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-20 overflow-hidden">
          <button
            onClick={handleExportPng}
            disabled={exporting}
            className="w-full px-4 py-2.5 text-left text-sm text-gray-200 hover:bg-gray-700 disabled:opacity-50 flex items-center gap-2"
          >
            <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14" />
            </svg>
            Export as PNG
          </button>
          <button
            onClick={handleExportJson}
            disabled={exporting}
            className="w-full px-4 py-2.5 text-left text-sm text-gray-200 hover:bg-gray-700 disabled:opacity-50 flex items-center gap-2"
          >
            <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            Export as JSON
          </button>
        </div>
      )}
    </div>
  );
}
