"use client";

import React from "react";

interface SparklineChartProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

function getTrendIndicator(data: number[]): { symbol: string; color: string } {
  if (data.length < 2) {
    return { symbol: "—", color: "text-gray-400" };
  }

  const first = data[0];
  const last = data[data.length - 1];

  if (last > first) {
    return { symbol: "↑", color: "text-green-500" };
  }
  if (last < first) {
    return { symbol: "↓", color: "text-red-500" };
  }
  return { symbol: "—", color: "text-gray-400" };
}

function buildPolylinePoints(
  data: number[],
  width: number,
  height: number,
  padding: number,
): string {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const drawWidth = width - padding * 2;
  const drawHeight = height - padding * 2;

  return data
    .map((value, index) => {
      const x = padding + (index / (data.length - 1)) * drawWidth;
      const y = padding + drawHeight - ((value - min) / range) * drawHeight;
      return `${x},${y}`;
    })
    .join(" ");
}

export default function SparklineChart({
  data,
  width = 80,
  height = 24,
  color = "#185FA5",
}: SparklineChartProps) {
  const padding = 2;
  const trend = getTrendIndicator(data);

  if (data.length === 0) {
    return null;
  }

  const points = buildPolylinePoints(data, width, height, padding);

  return (
    <span className="inline-flex items-center gap-1">
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible"
      >
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className={`text-xs font-medium ${trend.color}`}>
        {trend.symbol}
      </span>
    </span>
  );
}
