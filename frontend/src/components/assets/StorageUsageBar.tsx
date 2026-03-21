"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

interface StorageByType {
  image: number;
  audio: number;
  video: number;
}

interface StorageStats {
  used_gb: number;
  total_gb: number;
  by_type: StorageByType;
}

function formatGB(gb: number): string {
  if (gb < 0.01) return "0 GB";
  if (gb < 1) return `${(gb * 1024).toFixed(0)} MB`;
  return `${gb.toFixed(1)} GB`;
}

function getBarColor(pct: number): string {
  if (pct >= 80) return "bg-red-500";
  if (pct >= 60) return "bg-amber-500";
  return "bg-green-500";
}

function getTextColor(pct: number): string {
  if (pct >= 80) return "text-red-700";
  if (pct >= 60) return "text-amber-700";
  return "text-green-700";
}

export default function StorageUsageBar() {
  const { data, isLoading, error } = useQuery<StorageStats>({
    queryKey: ["storage-stats"],
    queryFn: async () => {
      const { data } = await api.get<StorageStats>("/api/assets/storage-stats");
      return data;
    },
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse rounded-lg border border-gray-200 bg-white p-4">
        <div className="h-4 w-48 rounded bg-gray-200" />
        <div className="mt-3 h-2 w-full rounded-full bg-gray-200" />
        <div className="mt-2 h-3 w-64 rounded bg-gray-200" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
        <p className="text-sm text-red-600">
          Failed to load storage stats.
        </p>
      </div>
    );
  }

  const pct = data.total_gb > 0 ? (data.used_gb / data.total_gb) * 100 : 0;
  const clampedPct = Math.min(pct, 100);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      {/* Header */}
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium text-gray-700">
          <span className={`font-semibold ${getTextColor(pct)}`}>
            {formatGB(data.used_gb)}
          </span>
          {" / "}
          {formatGB(data.total_gb)} used
        </p>
        <span className={`text-xs font-medium ${getTextColor(pct)}`}>
          {pct.toFixed(1)}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full transition-all duration-500 ${getBarColor(pct)}`}
          style={{ width: `${clampedPct}%` }}
        />
      </div>

      {/* Breakdown */}
      <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
        <span>
          Images:{" "}
          <span className="font-medium text-gray-700">
            {formatGB(data.by_type.image)}
          </span>
        </span>
        <span className="text-gray-300">|</span>
        <span>
          Audio:{" "}
          <span className="font-medium text-gray-700">
            {formatGB(data.by_type.audio)}
          </span>
        </span>
        <span className="text-gray-300">|</span>
        <span>
          Video:{" "}
          <span className="font-medium text-gray-700">
            {formatGB(data.by_type.video)}
          </span>
        </span>
      </div>
    </div>
  );
}
