"use client";

import { useState } from "react";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

export interface MemoryItem {
  id: string;
  content: string;
  category: string;
  scope: string;
  importance: number; // 1-10
  freshness_score: number; // 0-1
  access_count: number;
  source: string | null;
  is_private: boolean;
  tags: string[];
  created_at: string | null;
  last_accessed_at: string | null;
  decay_progress: number; // 0-1 (0 = fresh, 1 = fully decayed)
}

interface MemoryCardProps {
  memory: MemoryItem;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onDecayNow?: (id: string) => void;
  onPin?: (id: string) => void;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const CATEGORY_BADGE_COLORS: Record<string, string> = {
  fact: "bg-blue-100 text-blue-700",
  decision: "bg-purple-100 text-purple-700",
  observation: "bg-teal-100 text-teal-700",
  alert: "bg-red-100 text-red-700",
  preference: "bg-pink-100 text-pink-700",
  context: "bg-indigo-100 text-indigo-700",
  custom: "bg-gray-100 text-gray-700",
};

function heatBarColor(importance: number): string {
  if (importance >= 10) return "bg-red-500";
  if (importance >= 7) return "bg-green-500";
  if (importance >= 4) return "bg-amber-400";
  return "bg-gray-300";
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "never";
  const seconds = Math.floor(
    (Date.now() - new Date(dateStr).getTime()) / 1000,
  );
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

function decayBarColor(progress: number): string {
  if (progress < 0.3) return "bg-green-500";
  if (progress < 0.6) return "bg-amber-400";
  return "bg-red-500";
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function MemoryCard({
  memory,
  onEdit,
  onDelete,
  onDecayNow,
  onPin,
}: MemoryCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [hovered, setHovered] = useState(false);

  const badgeClass =
    CATEGORY_BADGE_COLORS[memory.category] ?? CATEGORY_BADGE_COLORS.custom;

  const needsShowMore = memory.content.length > 200;

  return (
    <div
      className="relative flex w-full rounded-xl border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md group"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Left importance heat bar */}
      <div
        className={`w-1.5 shrink-0 rounded-l-xl ${heatBarColor(memory.importance)}`}
      />

      {/* Main content area */}
      <div className="flex-1 min-w-0 p-4">
        {/* Top row: content */}
        <div className={expanded ? "" : "line-clamp-3"}>
          <p className="text-sm text-gray-800 whitespace-pre-wrap">
            {memory.content}
          </p>
        </div>
        {needsShowMore && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-brand-600 hover:text-brand-700 mt-1 font-medium"
          >
            {expanded ? "Show less" : "Show more"}
          </button>
        )}

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-2 mt-3">
          {/* Category badge */}
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${badgeClass}`}
          >
            {memory.category}
          </span>

          {/* Source */}
          {memory.source && (
            <span className="text-xs text-gray-400">
              via {memory.source}
            </span>
          )}

          {/* Private indicator */}
          {memory.is_private && (
            <span className="text-xs bg-red-50 text-red-500 px-1.5 py-0.5 rounded font-medium">
              Private
            </span>
          )}

          {/* Tags */}
          {memory.tags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Right panel: importance number + freshness */}
      <div className="shrink-0 w-40 border-l border-gray-100 p-4 flex flex-col justify-between">
        {/* Importance number */}
        <div className="text-right">
          <span
            className={`text-2xl font-bold ${
              memory.importance >= 10
                ? "text-red-500"
                : memory.importance >= 7
                  ? "text-green-600"
                  : memory.importance >= 4
                    ? "text-amber-500"
                    : "text-gray-400"
            }`}
          >
            {memory.importance}
          </span>
          <span className="text-xs text-gray-400 ml-1">/10</span>
        </div>

        {/* Freshness info */}
        <div className="mt-2 space-y-1.5">
          <p className="text-[10px] text-gray-400 leading-tight">
            Created {timeAgo(memory.created_at)}
            {memory.last_accessed_at && (
              <>
                {" "}
                &middot; Accessed {timeAgo(memory.last_accessed_at)}
              </>
            )}
          </p>

          {/* Decay progress bar */}
          <div>
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-[10px] text-gray-400">Decay</span>
              <span className="text-[10px] text-gray-400">
                {Math.round(memory.decay_progress * 100)}%
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full transition-all ${decayBarColor(memory.decay_progress)}`}
                style={{
                  width: `${Math.round(memory.decay_progress * 100)}%`,
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Hover actions overlay */}
      {hovered && (
        <div className="absolute top-2 right-2 flex gap-1 bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 shadow-sm p-1">
          {onEdit && (
            <button
              onClick={() => onEdit(memory.id)}
              className="p-1.5 text-gray-400 hover:text-brand-600 hover:bg-gray-100 rounded transition-colors"
              title="Edit"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(memory.id)}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Delete"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          )}
          {onDecayNow && (
            <button
              onClick={() => onDecayNow(memory.id)}
              className="p-1.5 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded transition-colors"
              title="Decay Now"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </button>
          )}
          {onPin && (
            <button
              onClick={() => onPin(memory.id)}
              className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
              title="Pin"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
                />
              </svg>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
