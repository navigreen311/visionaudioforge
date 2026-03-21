"use client";

import React from "react";

interface VisionSplitPaneProps {
  left: React.ReactNode;
  right: React.ReactNode;
}

/**
 * Two-column split-pane layout for the Vision page.
 *
 * - Left column: dropzone, operations, history controls.
 * - Right column: results area (BeforeAfterViewer, histogram, export).
 * - Collapses to a single column on screens < md breakpoint.
 */
export default function VisionSplitPane({ left, right }: VisionSplitPaneProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-[45fr_55fr]">
      {/* Left: controls */}
      <div className="space-y-6">{left}</div>

      {/* Right: results — sticky so it stays visible while scrolling controls */}
      <div className="md:sticky md:top-4 md:self-start">
        {right ?? (
          <div className="flex h-64 items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 text-sm text-gray-400">
            Run analysis to see results
          </div>
        )}
      </div>
    </div>
  );
}
