"use client";

import { useState } from "react";

export type AssetModality = "image" | "audio" | "video";

export interface SearchResult {
  asset_id: string;
  score: number;
  rank: number;
  asset_type: AssetModality | string;
  filename: string;
  path: string;
  tags?: string[];
  thumbnail_url?: string;
  size_bytes?: number;
  created_at?: string;
}

interface ResultCardProps {
  result: SearchResult;
  onClick: (result: SearchResult) => void;
}

function truncateFilename(name: string, maxLen = 20): string {
  if (!name || name.length <= maxLen) return name || "Untitled";
  const ext = name.lastIndexOf(".") !== -1 ? name.slice(name.lastIndexOf(".")) : "";
  const base = name.slice(0, maxLen - ext.length - 1);
  return `${base}...${ext}`;
}

function getScoreColor(score: number): string {
  const pct = Math.round(score * 100);
  if (pct >= 80) return "bg-green-100 text-green-700";
  if (pct >= 60) return "bg-amber-100 text-amber-700";
  return "bg-gray-100 text-gray-600";
}

const modalityConfig: Record<string, { bg: string; text: string; label: string }> = {
  image: { bg: "bg-blue-100", text: "text-blue-700", label: "Image" },
  audio: { bg: "bg-purple-100", text: "text-purple-700", label: "Audio" },
  video: { bg: "bg-red-100", text: "text-red-700", label: "Video" },
};

export default function ResultCard({ result, onClick }: ResultCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const scorePercent = Math.round(result.score * 100);
  const scoreColor = getScoreColor(result.score);

  const modality = modalityConfig[result.asset_type] ?? {
    bg: "bg-gray-100",
    text: "text-gray-600",
    label: result.asset_type || "Unknown",
  };

  const displayTags = (result.tags ?? []).slice(0, 3);

  return (
    <div
      onClick={() => onClick(result)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-all cursor-pointer group relative"
    >
      {/* Thumbnail / Icon */}
      <div className="aspect-square bg-gray-50 flex items-center justify-center relative">
        {result.thumbnail_url ? (
          <img
            src={result.thumbnail_url}
            alt={result.filename}
            className="w-full h-full object-cover"
          />
        ) : result.asset_type === "image" ? (
          <div className="w-full h-full bg-gray-200 flex items-center justify-center">
            <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        ) : result.asset_type === "audio" ? (
          <svg className="w-12 h-12 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        ) : result.asset_type === "video" ? (
          <svg className="w-12 h-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        ) : (
          <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        )}

        {/* Modality badge pill — top-right */}
        <span
          className={`absolute top-2 right-2 text-xs font-medium px-2 py-0.5 rounded-full ${modality.bg} ${modality.text}`}
        >
          {modality.label}
        </span>

        {/* Hover action row */}
        {isHovered && (
          <div className="absolute bottom-0 inset-x-0 bg-black/60 backdrop-blur-sm flex items-center justify-center gap-3 py-2 transition-opacity">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClick(result);
              }}
              className="text-white text-xs font-medium hover:text-blue-300 transition-colors"
              title="Preview"
            >
              Preview
            </button>
            <span className="text-white/40">|</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                // Placeholder: open in module
              }}
              className="text-white text-xs font-medium hover:text-blue-300 transition-colors"
              title="Open in module"
            >
              Open
            </button>
            <span className="text-white/40">|</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                // Placeholder: save / bookmark
              }}
              className="text-white text-xs font-medium hover:text-blue-300 transition-colors"
              title="Save"
            >
              Save
            </button>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3 space-y-2">
        {/* Filename */}
        <p className="text-sm font-medium text-gray-900 truncate group-hover:text-brand-600 transition-colors">
          {truncateFilename(result.filename)}
        </p>

        {/* Score pill + rank */}
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${scoreColor}`}>
            {scorePercent}%
          </span>
          <span className="text-xs text-gray-400">#{result.rank}</span>
        </div>

        {/* Tag pills (max 3) */}
        {displayTags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {displayTags.map((tag) => (
              <span
                key={tag}
                className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
