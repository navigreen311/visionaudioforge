"use client";

import React, { useCallback, useRef, useState } from "react";

interface ImageStats {
  min: number;
  max: number;
  mean: number;
  std: number;
}

interface BeforeAfterViewerProps {
  originalSrc: string;
  processedSrc: string | null;
  stats?: ImageStats;
}

export default function BeforeAfterViewer({
  originalSrc,
  processedSrc,
  stats,
}: BeforeAfterViewerProps) {
  const [dividerPosition, setDividerPosition] = useState(50);
  const [originalDims, setOriginalDims] = useState<{ w: number; h: number } | null>(null);
  const [processedDims, setProcessedDims] = useState<{ w: number; h: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const handleMouseDown = useCallback(() => {
    isDragging.current = true;
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setDividerPosition(pct);
  }, []);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  const handleOriginalLoad = useCallback(
    (e: React.SyntheticEvent<HTMLImageElement>) => {
      const img = e.currentTarget;
      setOriginalDims({ w: img.naturalWidth, h: img.naturalHeight });
    },
    []
  );

  const handleProcessedLoad = useCallback(
    (e: React.SyntheticEvent<HTMLImageElement>) => {
      const img = e.currentTarget;
      setProcessedDims({ w: img.naturalWidth, h: img.naturalHeight });
    },
    []
  );

  return (
    <div className="flex flex-col gap-4 md:flex-row md:gap-6">
      {/* Original panel */}
      <div className="flex-1">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Original
          {originalDims && (
            <span className="ml-1 font-normal text-gray-400">
              {originalDims.w} &times; {originalDims.h}px
            </span>
          )}
        </p>
        <img
          src={originalSrc}
          alt="Original"
          className="w-full rounded-lg border border-gray-200 object-contain"
          onLoad={handleOriginalLoad}
          draggable={false}
        />
      </div>

      {/* Processed panel */}
      <div className="flex-1">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Processed
          {processedDims && (
            <span className="ml-1 font-normal text-gray-400">
              {processedDims.w} &times; {processedDims.h}px
            </span>
          )}
        </p>

        {processedSrc ? (
          <>
            {/* Slider comparison container */}
            <div
              ref={containerRef}
              className="relative select-none overflow-hidden rounded-lg border border-gray-200"
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            >
              {/* Original layer (full width, clipped to left of divider) */}
              <img
                src={originalSrc}
                alt="Original comparison"
                className="block w-full object-contain"
                style={{
                  clipPath: `inset(0 ${100 - dividerPosition}% 0 0)`,
                }}
                draggable={false}
              />

              {/* Processed layer (absolute, clipped to right of divider) */}
              <img
                src={processedSrc}
                alt="Processed comparison"
                className="absolute inset-0 block w-full object-contain"
                style={{
                  clipPath: `inset(0 0 0 ${dividerPosition}%)`,
                }}
                onLoad={handleProcessedLoad}
                draggable={false}
              />

              {/* Draggable divider */}
              <div
                className="absolute top-0 bottom-0 z-10 w-1 cursor-col-resize bg-white shadow-lg"
                style={{ left: `${dividerPosition}%`, transform: "translateX(-50%)" }}
                onMouseDown={handleMouseDown}
              >
                <div className="absolute top-1/2 left-1/2 flex h-8 w-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white shadow-md">
                  <span className="text-xs text-gray-400">⟺</span>
                </div>
              </div>
            </div>

            {/* Stats row */}
            {stats && (
              <div className="mt-2 grid grid-cols-4 gap-2 rounded-lg border border-gray-200 bg-gray-50 p-2">
                <StatCell label="Min" value={stats.min} />
                <StatCell label="Max" value={stats.max} />
                <StatCell label="Mean" value={stats.mean} />
                <StatCell label="Std Dev" value={stats.std} />
              </div>
            )}
          </>
        ) : (
          <div className="flex h-48 items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 text-sm text-gray-400">
            Run analysis to see results
          </div>
        )}
      </div>
    </div>
  );
}

function StatCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center">
      <dt className="text-[10px] uppercase tracking-wide text-gray-500">{label}</dt>
      <dd className="text-sm font-medium text-gray-900">{value.toFixed(4)}</dd>
    </div>
  );
}
