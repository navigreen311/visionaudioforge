"use client";

import React from "react";

interface StatItem {
  label: string;
  value: string | number;
}

interface StatsPanelProps {
  title?: string;
  stats: StatItem[];
  className?: string;
}

export default function StatsPanel({ title, stats, className = "" }: StatsPanelProps) {
  return (
    <div
      className={`rounded-lg border border-gray-200 bg-gray-50 p-4 ${className}`}
    >
      {title && (
        <h4 className="mb-3 text-sm font-semibold text-gray-700">{title}</h4>
      )}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
        {stats.map((s) => (
          <div key={s.label}>
            <dt className="text-xs text-gray-500">{s.label}</dt>
            <dd className="text-sm font-medium text-gray-900">
              {typeof s.value === "number" ? s.value.toFixed(4) : s.value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
