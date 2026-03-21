"use client";

import React from "react";

const PALETTE = [
  "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
  "#06b6d4", "#ec4899", "#14b8a6", "#f97316", "#6366f1",
  "#84cc16", "#d946ef", "#0ea5e9", "#f43f5e", "#a855f7",
];

interface ClassDistributionChartProps {
  classCounts: Record<string, number>;
  maxBarWidth?: number;
}

export default function ClassDistributionChart({
  classCounts,
  maxBarWidth = 280,
}: ClassDistributionChartProps) {
  const entries = Object.entries(classCounts).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return null;

  const maxCount = Math.max(...entries.map(([, v]) => v));
  const rowHeight = 28;
  const labelWidth = 100;
  const countWidth = 50;
  const chartWidth = labelWidth + maxBarWidth + countWidth + 16;
  const svgHeight = entries.length * rowHeight + 4;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${chartWidth} ${svgHeight}`}
      className="overflow-visible"
      role="img"
      aria-label="Class distribution chart"
    >
      {entries.map(([className, count], i) => {
        const barWidth = maxCount > 0 ? (count / maxCount) * maxBarWidth : 0;
        const color = PALETTE[i % PALETTE.length];
        const y = i * rowHeight + 2;

        return (
          <g key={className}>
            {/* Class name label */}
            <text
              x={labelWidth - 8}
              y={y + rowHeight / 2}
              textAnchor="end"
              dominantBaseline="central"
              className="text-xs fill-gray-700"
              fontSize={11}
            >
              {className.length > 14 ? className.slice(0, 12) + "..." : className}
            </text>

            {/* Bar */}
            <rect
              x={labelWidth}
              y={y + 4}
              width={barWidth}
              height={rowHeight - 8}
              rx={3}
              fill={color}
              opacity={0.85}
            />

            {/* Count label */}
            <text
              x={labelWidth + barWidth + 6}
              y={y + rowHeight / 2}
              dominantBaseline="central"
              className="text-xs fill-gray-600"
              fontSize={11}
            >
              {count.toLocaleString()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
