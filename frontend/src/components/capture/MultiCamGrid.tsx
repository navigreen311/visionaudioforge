"use client";

import { useState } from "react";

export interface CaptureSource {
  source_id: string;
  source_type: string;
  status: string;
  is_primary: boolean;
  config: Record<string, unknown>;
  created_at: string;
}

interface MultiCamGridProps {
  sources: CaptureSource[];
  onSourceClick: (sourceId: string) => void;
  onRemoveSource: (sourceId: string) => void;
}

export default function MultiCamGrid({
  sources,
  onSourceClick,
  onRemoveSource,
}: MultiCamGridProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const gridCols =
    sources.length <= 1
      ? "grid-cols-1"
      : sources.length <= 4
      ? "grid-cols-2"
      : "grid-cols-3";

  if (expandedId) {
    const src = sources.find((s) => s.source_id === expandedId);
    return (
      <div className="relative">
        <div
          className="bg-gray-900 rounded-xl overflow-hidden cursor-pointer"
          style={{ aspectRatio: "16/9" }}
          onClick={() => setExpandedId(null)}
        >
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <p className="text-lg font-medium text-white">
                {src?.source_type.toUpperCase()} Feed
              </p>
              <p className="text-sm mt-1">Source: {expandedId.slice(0, 8)}</p>
              <p className="text-xs mt-2">Click to return to grid view</p>
            </div>
          </div>
        </div>
        <div className="absolute top-2 left-2 flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              src?.status === "active" ? "bg-green-500" : "bg-gray-400"
            }`}
          />
          <span className="text-white text-xs bg-black/50 px-2 py-0.5 rounded">
            {src?.source_type} — {src?.is_primary ? "PRIMARY" : "secondary"}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={`grid ${gridCols} gap-2`}>
      {sources.map((src) => (
        <div
          key={src.source_id}
          className={`relative bg-gray-900 rounded-lg overflow-hidden cursor-pointer border-2 transition-colors ${
            src.is_primary
              ? "border-brand-500"
              : "border-transparent hover:border-gray-600"
          }`}
          style={{ aspectRatio: "16/9" }}
          onClick={() => setExpandedId(src.source_id)}
        >
          {/* Placeholder feed area */}
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-sm font-medium text-gray-300">
                {src.source_type.toUpperCase()}
              </p>
              <p className="text-xs mt-0.5">{src.source_id.slice(0, 8)}</p>
            </div>
          </div>

          {/* Status overlay */}
          <div className="absolute top-1.5 left-1.5 flex items-center gap-1">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                src.status === "active" ? "bg-green-500" : "bg-gray-400"
              }`}
            />
            <span className="text-white text-[10px] bg-black/50 px-1.5 py-0.5 rounded">
              {src.source_type}
            </span>
          </div>

          {/* Actions */}
          <div className="absolute top-1.5 right-1.5 flex gap-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSourceClick(src.source_id);
              }}
              className="text-[10px] bg-brand-600 hover:bg-brand-700 text-white px-1.5 py-0.5 rounded"
            >
              Set Primary
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRemoveSource(src.source_id);
              }}
              className="text-[10px] bg-red-600 hover:bg-red-700 text-white px-1.5 py-0.5 rounded"
            >
              X
            </button>
          </div>

          {src.is_primary && (
            <div className="absolute bottom-1.5 left-1.5">
              <span className="text-[10px] bg-brand-600 text-white px-1.5 py-0.5 rounded">
                PRIMARY
              </span>
            </div>
          )}
        </div>
      ))}

      {sources.length === 0 && (
        <div
          className="col-span-full flex items-center justify-center bg-gray-100 rounded-xl border-2 border-dashed border-gray-300"
          style={{ aspectRatio: "16/9" }}
        >
          <p className="text-gray-400 text-sm">
            No sources added. Use the sidebar to add capture sources.
          </p>
        </div>
      )}
    </div>
  );
}
