"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ActivityType = "capture" | "alert" | "pipeline" | "model" | "upload" | "search";

interface ActivityItem {
  type: string;
  message: string;
  timestamp: string;
  severity?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const BORDER_BY_TYPE: Record<ActivityType, string> = {
  capture: "border-l-blue-500",
  alert: "border-l-red-500",
  pipeline: "border-l-purple-500",
  model: "border-l-teal-500",
  upload: "border-l-gray-400",
  search: "border-l-amber-500",
};

function borderForType(type: string): string {
  return BORDER_BY_TYPE[type as ActivityType] ?? "border-l-gray-300";
}

function timeAgo(date: string): string {
  const now = Date.now();
  const then = new Date(date).getTime();
  const diffSeconds = Math.max(0, Math.floor((now - then) / 1000));

  if (diffSeconds < 60) return "just now";

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes} min ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;

  const diffMonths = Math.floor(diffDays / 30);
  return `${diffMonths}mo ago`;
}

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------

function SkeletonRow() {
  return (
    <div className="flex items-start gap-3 border-l-4 border-l-gray-200 bg-white p-3 animate-pulse">
      <div className="flex-1 space-y-2">
        <div className="h-3 w-3/4 rounded bg-gray-200" />
        <div className="h-2.5 w-1/3 rounded bg-gray-100" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 10_000;

export default function ActivityFeed() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchActivity = useCallback(async () => {
    try {
      const { data } = await api.get<ActivityItem[]>("/api/dashboard/activity", {
        params: { limit: 20 },
      });
      setItems(data);
      setError(null);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to load activity";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActivity();

    const interval = setInterval(fetchActivity, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchActivity]);

  const handleClear = () => {
    setItems([]);
  };

  // --- Loading state --------------------------------------------------

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-900">Activity</h3>
        </div>
        <div className="divide-y divide-gray-100">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonRow key={i} />
          ))}
        </div>
      </div>
    );
  }

  // --- Error state ----------------------------------------------------

  if (error) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-900">Activity</h3>
        </div>
        <div className="flex flex-col items-center gap-3 px-4 py-8 text-center">
          <p className="text-sm text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              fetchActivity();
            }}
            className="rounded-md bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-200"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // --- Main render ----------------------------------------------------

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-900">Activity</h3>
        <div className="flex items-center gap-2">
          {items.length > 0 && (
            <button
              type="button"
              onClick={handleClear}
              className="text-xs font-medium text-gray-500 transition-colors hover:text-gray-700"
            >
              Clear
            </button>
          )}
          <Link
            href="/alerts"
            className="text-xs font-medium text-blue-600 transition-colors hover:text-blue-700"
          >
            View all
          </Link>
        </div>
      </div>

      {/* Body */}
      {items.length === 0 ? (
        <div className="px-4 py-8 text-center">
          <p className="text-sm text-gray-400">
            Workspace activity will appear here
          </p>
        </div>
      ) : (
        <div className="divide-y divide-gray-100">
          {items.map((item, idx) => (
            <div
              key={`${item.timestamp}-${idx}`}
              className={`border-l-4 ${borderForType(item.type)} px-4 py-3 transition-colors hover:bg-gray-50`}
            >
              <p className="text-sm text-gray-800">{item.message}</p>
              <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                <span className="capitalize">{item.type}</span>
                <span aria-hidden="true">&middot;</span>
                <span>{timeAgo(item.timestamp)}</span>
                {item.severity && (
                  <>
                    <span aria-hidden="true">&middot;</span>
                    <span className="capitalize">{item.severity}</span>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
