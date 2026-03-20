"use client";

import React from "react";
import VideoPanel from "./VideoPanel";
import type { GridLayout, Stream } from "@/lib/api";

interface VideoWallProps {
  layout: GridLayout;
  streams: Stream[];
  onClickEnlarge?: (stream: Stream) => void;
  onDoubleClickPrimary?: (stream: Stream) => void;
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
  onClickEnlarge,
  onDoubleClickPrimary,
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
          ? { gridRow: `1 / -1` }
          : {};

        return (
          <div key={stream?.id ?? `empty-${i}`} style={spanStyle}>
            <VideoPanel
              stream={stream}
              onClickEnlarge={onClickEnlarge}
              onDoubleClickPrimary={onDoubleClickPrimary}
              onAddStream={onAddStream}
            />
          </div>
        );
      })}
    </div>
  );
}
