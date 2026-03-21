"use client";

import React from "react";
import Card from "@/components/ui/Card";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SimulationProgressProps {
  /** Current event index (0-based). -1 means indeterminate / starting. */
  currentEvent: number;
  /** Total events to generate. */
  totalEvents: number;
  /** Whether the simulation is actively running. */
  running: boolean;
  /** Callback when user clicks Cancel. */
  onCancel: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SimulationProgress({
  currentEvent,
  totalEvents,
  running,
  onCancel,
}: SimulationProgressProps) {
  const isIndeterminate = currentEvent < 0;
  const pct = isIndeterminate ? 0 : Math.min(100, Math.round(((currentEvent + 1) / totalEvents) * 100));

  if (!running) return null;

  return (
    <Card>
      <div className="space-y-4">
        {/* Status text */}
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-gray-700">
            {isIndeterminate
              ? "Initializing simulation..."
              : `Generating event ${currentEvent + 1} of ${totalEvents}...`}
          </p>
          <span className="text-xs font-mono text-gray-500">
            {isIndeterminate ? "--%" : `${pct}%`}
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
          {isIndeterminate ? (
            <div className="h-full w-1/3 animate-[indeterminate_1.5s_ease-in-out_infinite] rounded-full bg-brand-500" />
          ) : (
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          )}
        </div>

        {/* Cancel button */}
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Cancel
          </button>
        </div>
      </div>

      {/* Inline keyframes for indeterminate animation */}
      <style jsx>{`
        @keyframes indeterminate {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(200%); }
          100% { transform: translateX(-100%); }
        }
      `}</style>
    </Card>
  );
}
