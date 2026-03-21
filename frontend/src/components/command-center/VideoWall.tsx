"use client";

import React from "react";
import StreamCell from "./StreamCell";
import type { GridLayout, Stream } from "@/lib/api";

interface VideoWallProps {
  layout: GridLayout;
  streams: Stream[];
  onRemoveStream: (streamId: string) => void;
  onAddStream?: () => void;
}

function getGridConfig(layout: GridLayout): {
  style: React.CSSProperties;
  totalSlots: number;
  primaryIndex?: number;
} {
  switch (layout) {
    case "2x2":
      return {
        style: {
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gridTemplateRows: "1fr 1fr",
          gap: "4px",
        },
        totalSlots: 4,
      };
    case "3x3":
      return {
        style: {
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gridTemplateRows: "1fr 1fr 1fr",
          gap: "4px",
        },
        totalSlots: 9,
      };
    case "4x4":
      return {
        style: {
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr",
          gridTemplateRows: "1fr 1fr 1fr 1fr",
          gap: "4px",
        },
        totalSlots: 16,
      };
    case "1+3":
      return {
        style: {
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gridTemplateRows: "1fr 1fr 1fr",
          gap: "4px",
        },
        totalSlots: 4,
        primaryIndex: 0,
      };
    case "1+5":
      return {
        style: {
          display: "grid",
          gridTemplateColumns: "2fr 1fr",
          gridTemplateRows: "1fr 1fr 1fr 1fr 1fr",
          gap: "4px",
        },
        totalSlots: 6,
        primaryIndex: 0,
      };
    default:
      return {
        style: {
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gridTemplateRows: "1fr 1fr",
          gap: "4px",
        },
        totalSlots: 4,
      };
  }
}

export default function VideoWall({
  layout,
  streams,
  onRemoveStream,
  onAddStream,
}: VideoWallProps) {
  const { style, totalSlots, primaryIndex } = getGridConfig(layout);

  // Sort streams so primary comes first for 1+N layouts
  const sorted = [...streams].sort((a, b) => {
    if (a.is_primary && !b.is_primary) return -1;
    if (!a.is_primary && b.is_primary) return 1;
    return a.position - b.position;
  });

  const slots: (Stream | undefined)[] = [];
  for (let i = 0; i < totalSlots; i++) {
    slots.push(sorted[i] || undefined);
  }

  return (
    <div className="h-full w-full rounded-lg bg-gray-950 p-1" style={style}>
      {slots.map((stream, i) => {
        const isPrimarySlot = primaryIndex !== undefined && i === primaryIndex;
        const spanStyle: React.CSSProperties = isPrimarySlot
          ? { gridRow: "1 / -1" }
          : {};

        if (!stream) {
          return (
            <div
              key={`empty-${i}`}
              style={spanStyle}
              className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-900/5 h-full min-h-[140px]"
            >
              <svg
                className="h-10 w-10 text-gray-300 mb-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              <span className="text-sm text-gray-400 mb-2">No Stream</span>
              <button
                onClick={onAddStream}
                className="rounded-md bg-brand-600 px-3 py-1 text-xs font-medium text-white hover:bg-brand-700 transition-colors"
              >
                Add Stream
              </button>
            </div>
          );
        }

        return (
          <div key={stream.id} style={spanStyle}>
            <StreamCell
              stream={stream}
              onRemove={onRemoveStream}
              gridSize={layout}
            />
          </div>
        );
      })}
    </div>
  );
}
