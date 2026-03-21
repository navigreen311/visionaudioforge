"use client";

import React, { useState } from "react";

interface HeatmapViewerProps {
  originalSrc: string;
  heatmapB64?: string | null;
}

export default function HeatmapViewer({
  originalSrc,
  heatmapB64,
}: HeatmapViewerProps) {
  const [opacity, setOpacity] = useState(50);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Original image */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">Original</p>
          <div className="flex items-center justify-center rounded-lg border border-gray-200 bg-gray-900 p-2">
            <img
              src={originalSrc}
              alt="Original input"
              className="max-h-72 object-contain"
            />
          </div>
        </div>

        {/* Heatmap overlay */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">
            Heatmap Overlay
          </p>
          <div className="relative flex items-center justify-center rounded-lg border border-gray-200 bg-gray-900 p-2 overflow-hidden">
            {heatmapB64 ? (
              <>
                <img
                  src={originalSrc}
                  alt="Base layer"
                  className="max-h-72 object-contain"
                />
                <img
                  src={`data:image/png;base64,${heatmapB64}`}
                  alt="Heatmap overlay"
                  className="absolute inset-0 m-auto max-h-72 object-contain"
                  style={{ opacity: opacity / 100 }}
                />
              </>
            ) : (
              <div className="flex h-72 w-full items-center justify-center">
                <div className="text-center">
                  <svg
                    className="mx-auto mb-2 h-12 w-12 text-gray-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                  <p className="text-sm text-gray-400">
                    No heatmap available
                  </p>
                  <p className="text-xs text-gray-500">
                    Generate an explanation to see the overlay
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Opacity slider */}
      {heatmapB64 && (
        <div className="flex items-center gap-3">
          <label
            htmlFor="heatmap-opacity"
            className="text-sm font-medium text-gray-700 whitespace-nowrap"
          >
            Overlay Opacity
          </label>
          <input
            id="heatmap-opacity"
            type="range"
            min={0}
            max={100}
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
            className="flex-1 accent-brand-600"
          />
          <span className="w-10 text-right text-sm text-gray-600">
            {opacity}%
          </span>
        </div>
      )}
    </div>
  );
}
