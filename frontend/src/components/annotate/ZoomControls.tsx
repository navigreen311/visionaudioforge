"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/* ------------------------------------------------------------------ */
/*  ZoomControls – bottom-of-canvas zoom bar                           */
/* ------------------------------------------------------------------ */

const MIN_ZOOM = 0.25; // 25%
const MAX_ZOOM = 4.0; // 400%
const ZOOM_STEP = 0.1;

function clampZoom(value: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));
}

interface ZoomControlsProps {
  zoom: number;
  onZoomChange: (zoom: number) => void;
  /** Optional ref to the container element for fit-to-screen and scroll zoom */
  containerRef?: React.RefObject<HTMLElement | null>;
  /** Natural image dimensions for fit-to-screen */
  imageSize?: { w: number; h: number };
}

export default function ZoomControls({
  zoom,
  onZoomChange,
  containerRef,
  imageSize,
}: ZoomControlsProps) {
  const [editing, setEditing] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  /* ---------- zoom in / out handlers ---------- */
  const zoomIn = useCallback(() => {
    onZoomChange(clampZoom(zoom + ZOOM_STEP));
  }, [zoom, onZoomChange]);

  const zoomOut = useCallback(() => {
    onZoomChange(clampZoom(zoom - ZOOM_STEP));
  }, [zoom, onZoomChange]);

  const fitToScreen = useCallback(() => {
    if (!containerRef?.current || !imageSize || imageSize.w === 0 || imageSize.h === 0) {
      onZoomChange(1);
      return;
    }
    const el = containerRef.current;
    const scaleX = el.clientWidth / imageSize.w;
    const scaleY = el.clientHeight / imageSize.h;
    onZoomChange(clampZoom(Math.min(scaleX, scaleY)));
  }, [containerRef, imageSize, onZoomChange]);

  /* ---------- editable percentage field ---------- */
  const startEditing = () => {
    setInputValue(String(Math.round(zoom * 100)));
    setEditing(true);
    // Focus after state update
    requestAnimationFrame(() => inputRef.current?.select());
  };

  const commitEdit = () => {
    setEditing(false);
    const parsed = parseInt(inputValue, 10);
    if (!Number.isNaN(parsed) && parsed > 0) {
      onZoomChange(clampZoom(parsed / 100));
    }
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      commitEdit();
    } else if (e.key === "Escape") {
      setEditing(false);
    }
  };

  /* ---------- Ctrl + scroll wheel ---------- */
  useEffect(() => {
    const target = containerRef?.current ?? document;

    const handler = (e: Event) => {
      const we = e as WheelEvent;
      if (!we.ctrlKey) return;
      we.preventDefault();
      const delta = we.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
      onZoomChange(clampZoom(zoom + delta));
    };

    target.addEventListener("wheel", handler, { passive: false });
    return () => target.removeEventListener("wheel", handler);
  }, [zoom, onZoomChange, containerRef]);

  /* ---------- keyboard shortcuts: Ctrl+= / Ctrl+- / Ctrl+0 ---------- */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.key === "=" || e.key === "+") {
        e.preventDefault();
        onZoomChange(clampZoom(zoom + ZOOM_STEP));
      } else if (e.key === "-") {
        e.preventDefault();
        onZoomChange(clampZoom(zoom - ZOOM_STEP));
      } else if (e.key === "0") {
        e.preventDefault();
        onZoomChange(1);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [zoom, onZoomChange]);

  return (
    <div className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-1 py-0.5 shadow-sm">
      {/* Zoom out */}
      <button
        type="button"
        onClick={zoomOut}
        disabled={zoom <= MIN_ZOOM}
        title="Zoom out"
        className="inline-flex h-7 w-7 items-center justify-center rounded text-gray-600 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M20 12H4" />
        </svg>
      </button>

      {/* Zoom percentage – click to type */}
      {editing ? (
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value.replace(/[^0-9]/g, ""))}
          onBlur={commitEdit}
          onKeyDown={handleInputKeyDown}
          className="w-14 rounded border border-brand-300 bg-brand-50 px-1 py-0.5 text-center text-xs font-medium text-gray-800 outline-none"
          aria-label="Zoom percentage"
        />
      ) : (
        <button
          type="button"
          onClick={startEditing}
          title="Click to set zoom"
          className="w-14 rounded px-1 py-0.5 text-center text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
        >
          {Math.round(zoom * 100)}%
        </button>
      )}

      {/* Zoom in */}
      <button
        type="button"
        onClick={zoomIn}
        disabled={zoom >= MAX_ZOOM}
        title="Zoom in"
        className="inline-flex h-7 w-7 items-center justify-center rounded text-gray-600 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </button>

      {/* Fit to screen */}
      <div className="mx-0.5 h-4 w-px bg-gray-200" />
      <button
        type="button"
        onClick={fitToScreen}
        title="Fit to screen"
        className="inline-flex h-7 w-7 items-center justify-center rounded text-gray-600 transition-colors hover:bg-gray-100"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5"
          />
        </svg>
      </button>
    </div>
  );
}
