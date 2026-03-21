"use client";

import React from "react";

interface Percentiles {
  p50: number;
  p95: number;
  p99: number;
}

interface LatencyHistogramProps {
  data: number[];
  percentiles: Percentiles;
}

const WIDTH = 320;
const HEIGHT = 160;
const PADDING = { top: 12, right: 12, bottom: 28, left: 36 };
const CHART_W = WIDTH - PADDING.left - PADDING.right;
const CHART_H = HEIGHT - PADDING.top - PADDING.bottom;
const BIN_COUNT = 20;

function buildBins(data: number[]): { start: number; end: number; count: number }[] {
  if (data.length === 0) return [];
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = range / BIN_COUNT;

  const bins = Array.from({ length: BIN_COUNT }, (_, i) => ({
    start: min + i * step,
    end: min + (i + 1) * step,
    count: 0,
  }));

  for (const v of data) {
    const idx = Math.min(Math.floor((v - min) / step), BIN_COUNT - 1);
    bins[idx].count++;
  }
  return bins;
}

export default function LatencyHistogram({ data, percentiles }: LatencyHistogramProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-gray-200 bg-gray-50 text-sm text-gray-400" style={{ width: WIDTH, height: HEIGHT }}>
        No latency data
      </div>
    );
  }

  const bins = buildBins(data);
  const maxCount = Math.max(...bins.map((b) => b.count), 1);
  const minVal = bins[0].start;
  const maxVal = bins[bins.length - 1].end;
  const valRange = maxVal - minVal || 1;

  const barWidth = CHART_W / BIN_COUNT - 1;

  const toX = (v: number) => PADDING.left + ((v - minVal) / valRange) * CHART_W;
  const toY = (count: number) => PADDING.top + CHART_H - (count / maxCount) * CHART_H;

  const pLines: { value: number; label: string; color: string }[] = [
    { value: percentiles.p50, label: "p50", color: "#2563eb" },
    { value: percentiles.p95, label: "p95", color: "#f59e0b" },
    { value: percentiles.p99, label: "p99", color: "#ef4444" },
  ];

  // Y-axis ticks
  const yTicks = [0, Math.round(maxCount / 2), maxCount];

  return (
    <svg
      width={WIDTH}
      height={HEIGHT}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="rounded-lg border border-gray-200 bg-gray-900"
    >
      {/* Y-axis labels */}
      {yTicks.map((t) => (
        <text
          key={`yt-${t}`}
          x={PADDING.left - 4}
          y={toY(t) + 3}
          textAnchor="end"
          className="fill-gray-400"
          fontSize={8}
        >
          {t}
        </text>
      ))}

      {/* X-axis label */}
      <text
        x={PADDING.left + CHART_W / 2}
        y={HEIGHT - 2}
        textAnchor="middle"
        className="fill-gray-400"
        fontSize={8}
      >
        Latency (ms)
      </text>

      {/* X-axis tick labels */}
      <text x={PADDING.left} y={HEIGHT - 14} textAnchor="start" className="fill-gray-500" fontSize={7}>
        {minVal.toFixed(1)}
      </text>
      <text x={PADDING.left + CHART_W} y={HEIGHT - 14} textAnchor="end" className="fill-gray-500" fontSize={7}>
        {maxVal.toFixed(1)}
      </text>

      {/* Bars */}
      {bins.map((bin, i) => {
        const x = PADDING.left + i * (CHART_W / BIN_COUNT) + 0.5;
        const h = (bin.count / maxCount) * CHART_H;
        return (
          <rect
            key={`bar-${i}`}
            x={x}
            y={PADDING.top + CHART_H - h}
            width={barWidth}
            height={h}
            rx={1}
            className="fill-blue-500 opacity-70"
          />
        );
      })}

      {/* Percentile dashed lines */}
      {pLines.map((pl) => {
        if (pl.value < minVal || pl.value > maxVal) return null;
        const x = toX(pl.value);
        return (
          <g key={pl.label}>
            <line
              x1={x}
              y1={PADDING.top}
              x2={x}
              y2={PADDING.top + CHART_H}
              stroke={pl.color}
              strokeWidth={1.5}
              strokeDasharray="4 2"
            />
            <text
              x={x + 2}
              y={PADDING.top + 8}
              fill={pl.color}
              fontSize={7}
              fontWeight="bold"
            >
              {pl.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
