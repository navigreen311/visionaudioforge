"use client";

import { useCallback, useRef, useState } from "react";

interface ImageInfo {
  width: number;
  height: number;
  size: string;
}

interface BeforeAfterViewerProps {
  originalSrc?: string;
  transformedSrc?: string;
  originalInfo?: ImageInfo;
  transformedInfo?: ImageInfo;
}

export default function BeforeAfterViewer({
  originalSrc,
  transformedSrc,
  originalInfo,
  transformedInfo,
}: BeforeAfterViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState(50);
  const [dragging, setDragging] = useState(false);

  const updatePosition = useCallback((clientX: number) => {
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const x = clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setPosition(pct);
  }, []);

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      setDragging(true);
      updatePosition(e.clientX);
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [updatePosition],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragging) return;
      updatePosition(e.clientX);
    },
    [dragging, updatePosition],
  );

  const onPointerUp = useCallback(() => {
    setDragging(false);
  }, []);

  const hasImages = originalSrc && transformedSrc;

  if (!hasImages) {
    return (
      <div className="flex items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50"
        style={{ minHeight: "320px" }}
      >
        <div className="text-center px-6 py-10">
          <svg
            className="mx-auto h-12 w-12 text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
            />
          </svg>
          <p className="mt-3 text-sm font-medium text-gray-500">
            Run a transform to see results
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Upload an image and apply a transformation to compare before and after
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Viewer with draggable divider */}
      <div
        ref={containerRef}
        className="relative w-full select-none overflow-hidden rounded-lg border border-gray-200 bg-gray-900"
        style={{ aspectRatio: "16 / 9" }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        {/* Transformed image (full width, behind) */}
        <img
          src={transformedSrc}
          alt="Transformed"
          className="absolute inset-0 h-full w-full object-contain"
          draggable={false}
        />

        {/* Original image (clipped via clip-path) */}
        <div
          className="absolute inset-0"
          style={{
            clipPath: `inset(0 ${100 - position}% 0 0)`,
          }}
        >
          <img
            src={originalSrc}
            alt="Original"
            className="absolute inset-0 h-full w-full object-contain"
            draggable={false}
          />
        </div>

        {/* Divider line */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white/80 shadow-md pointer-events-none"
          style={{ left: `${position}%`, transform: "translateX(-50%)" }}
        >
          {/* Handle */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex h-10 w-10 cursor-ew-resize items-center justify-center rounded-full bg-white shadow-lg pointer-events-auto">
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              className="text-gray-600"
            >
              <path
                d="M7 4l-4 6 4 6M13 4l4 6-4 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </div>

        {/* Labels */}
        <span className="absolute top-3 left-3 rounded bg-black/60 px-2.5 py-1 text-xs font-medium text-white backdrop-blur-sm">
          Original
          {originalInfo && (
            <span className="ml-1.5 text-white/70">
              {originalInfo.width}x{originalInfo.height} &middot; {originalInfo.size}
            </span>
          )}
        </span>
        <span className="absolute top-3 right-3 rounded px-2.5 py-1 text-xs font-medium text-white backdrop-blur-sm"
          style={{ backgroundColor: "rgba(15, 110, 86, 0.75)" }}
        >
          Transformed
          {transformedInfo && (
            <span className="ml-1.5 text-white/80">
              {transformedInfo.width}x{transformedInfo.height} &middot; {transformedInfo.size}
            </span>
          )}
        </span>
      </div>

      {/* Position indicator */}
      <div className="flex items-center justify-center">
        <span className="text-xs text-gray-400">
          Drag the divider to compare &middot; {Math.round(position)}%
        </span>
      </div>
    </div>
  );
}
