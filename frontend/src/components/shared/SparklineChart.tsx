"use client";

import React, { useMemo } from "react";

interface SparklineChartProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

interface TrendIndicator {
  symbol: string;
  colorClass: string;
  strokeColor: string;
}

function getTrendIndicator(data: number[]): TrendIndicator {
  if (data.length < 2) {
    return { symbol: "\u2014", colorClass: "text-gray-400", strokeColor: "#9CA3AF" };
  }

  const first = data[0];
  const last = data[data.length - 1];
  const threshold = Math.abs(first) * 0.01; // 1% threshold for "flat"

  if (last - first > threshold) {
    return { symbol: "\u2191", colorClass: "text-[#0F6E56]", strokeColor: "#0F6E56" };
  }
  if (first - last > threshold) {
    return { symbol: "\u2193", colorClass: "text-[#A32D2D]", strokeColor: "#A32D2D" };
  }
  return { symbol: "\u2014", colorClass: "text-gray-400", strokeColor: "#9CA3AF" };
}

function normalizeToPoints(
  data: number[],
  width: number,
  height: number,
  padding: number,
): Array<{ x: number; y: number }> {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const drawWidth = width - padding * 2;
  const drawHeight = height - padding * 2;
  const step = data.length > 1 ? drawWidth / (data.length - 1) : 0;

  return data.map((value, index) => ({
    x: padding + index * step,
    y: padding + drawHeight - ((value - min) / range) * drawHeight,
  }));
}

function sampleToFixedPoints(data: number[], count: number): number[] {
  if (data.length <= count) return data;

  const result: number[] = [];
  for (let i = 0; i < count; i++) {
    const index = Math.round((i / (count - 1)) * (data.length - 1));
    result.push(data[index]);
  }
  return result;
}

export default function SparklineChart({
  data,
  width = 80,
  height = 28,
  color = "#185FA5",
}: SparklineChartProps) {
  const padding = 3;

  const { points, polylineStr, areaPath, trend, gradientId } = useMemo(() => {
    if (data.length === 0) {
      return { points: [], polylineStr: "", areaPath: "", trend: getTrendIndicator([]), gradientId: "" };
    }

    const sampled = sampleToFixedPoints(data, 7);
    const trendResult = getTrendIndicator(sampled);
    const pts = normalizeToPoints(sampled, width, height, padding);
    const lineStr = pts.map((p) => `${p.x},${p.y}`).join(" ");

    // Build closed area path for gradient fill
    const firstPt = pts[0];
    const lastPt = pts[pts.length - 1];
    const bottomY = height - padding;
    const area =
      `M ${firstPt.x},${bottomY} ` +
      pts.map((p) => `L ${p.x},${p.y}`).join(" ") +
      ` L ${lastPt.x},${bottomY} Z`;

    const id = `spark-grad-${Math.random().toString(36).slice(2, 8)}`;

    return { points: pts, polylineStr: lineStr, areaPath: area, trend: trendResult, gradientId: id };
  }, [data, width, height]);

  if (data.length === 0) {
    return null;
  }

  const strokeColor = trend.strokeColor === "#9CA3AF" ? color : trend.strokeColor;

  return (
    <span className="inline-flex items-center gap-1.5" role="img" aria-label="Sparkline trend chart">
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity={0.2} />
            <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        <path d={areaPath} fill={`url(#${gradientId})`} />
        <polyline
          points={polylineStr}
          fill="none"
          stroke={strokeColor}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* End-point dot */}
        {points.length > 0 && (
          <circle
            cx={points[points.length - 1].x}
            cy={points[points.length - 1].y}
            r={2}
            fill={strokeColor}
          />
        )}
      </svg>
      <span className={`text-xs font-semibold leading-none ${trend.colorClass}`}>
        {trend.symbol}
      </span>
    </span>
  );
}
