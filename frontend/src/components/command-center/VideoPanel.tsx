"use client";

import React from "react";
import type { Stream } from "@/lib/api";

interface VideoPanelProps {
  stream?: Stream;
  onClickEnlarge?: (stream: Stream) => void;
  onDoubleClickPrimary?: (stream: Stream) => void;
  onAddStream?: () => void;
}

const statusColors: Record<string, string> = {
  online: "bg-green-500",
  offline: "bg-gray-400",
  degraded: "bg-yellow-500",
};

export default function VideoPanel({
  stream,
  onClickEnlarge,
  onDoubleClickPrimary,
  onAddStream,
}: VideoPanelProps) {
  if (!stream) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-900/5 h-full min-h-[140px]">
        <svg className="h-10 w-10 text-gray-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
    <div
      className="relative flex flex-col rounded-lg bg-gray-900 h-full min-h-[140px] overflow-hidden cursor-pointer group"
      onClick={() => onClickEnlarge?.(stream)}
      onDoubleClick={() => onDoubleClickPrimary?.(stream)}
    >
      {/* Simulated video feed area */}
      <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-800 to-gray-900">
        <svg className="h-16 w-16 text-gray-600 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1}
            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
      </div>

      {/* Top bar overlay */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-3 py-1.5 bg-gradient-to-b from-black/60 to-transparent">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${statusColors[stream.status] || "bg-gray-400"}`} />
          <span className="text-xs font-medium text-white truncate max-w-[120px]">
            {stream.name}
          </span>
        </div>
        <span className="text-[10px] text-gray-300 font-mono">
          {stream.fps} FPS
        </span>
      </div>

      {/* Enlarge overlay on hover */}
      <div className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/30 transition-colors">
        <svg
          className="h-8 w-8 text-white opacity-0 group-hover:opacity-80 transition-opacity"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
          />
        </svg>
      </div>

      {/* Primary badge */}
      {stream.is_primary && (
        <div className="absolute bottom-2 left-2 rounded bg-brand-600 px-1.5 py-0.5 text-[10px] font-bold text-white uppercase tracking-wide">
          Primary
        </div>
      )}
    </div>
  );
}
