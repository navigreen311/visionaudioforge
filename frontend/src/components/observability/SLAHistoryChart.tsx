"use client";

import React, { useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DayCompliance {
  /** ISO date string (YYYY-MM-DD) */
  date: string;
  /** Compliance percentage 0-100 */
  pct: number;
}

interface TooltipState {
  x: number;
  y: number;
  day: DayCompliance;
}

interface SLAHistoryChartProps {
  data: DayCompliance[];
  /** Target compliance percentage (default 99.9) */
  targetPct?: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const CHART_HEIGHT = 160;
const PADDING = { top: 14, right: 12, bottom: 26, left: 36 };
const DOT_RADIUS = 1.2;
const VIEWBOX_WIDTH = 100;
const COLOR_OK = "#22c55e";    // green-500
const COLOR_FAIL = "#ef4444";  // red-500

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function SLAHistoryChart({ data, targetPct = 99.9 }: SLAHistoryChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const usableW = VIEWBOX_WIDTH - PADDING.left - PADDING.right;
  const usableH = CHART_HEIGHT - PADDING.top - PADDING.bottom;

  // Y-range: show from min(data)-1 to 100, but never below 90
  const minPct = Math.max(Math.min(...data.map((d) => d.pct), targetPct) - 1, 90);
  const maxPct = 100;
  const yRange = maxPct - minPct || 1;

  function toX(i: number): number {
    return PADDING.left + (i / Math.max(data.length - 1, 1)) * usableW;
  }

  function toY(pct: number): number {
    return PADDING.top + usableH - ((pct - minPct) / yRange) * usableH;
  }

  // Build polyline points
  const points = data.map((d, i) => ({ x: toX(i), y: toY(d.pct), day: d }));

  // Build line segments, coloring red when below threshold
  const segments: { x1: number; y1: number; x2: number; y2: number; below: boolean }[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const belowThreshold = data[i].pct < targetPct || data[i + 1].pct < targetPct;
    segments.push({
      x1: points[i].x,
      y1: points[i].y,
      x2: points[i + 1].x,
      y2: points[i + 1].y,
      below: belowThreshold,
    });
  }

  const thresholdY = toY(targetPct);

  // Y-axis ticks
  const yTicks = [minPct, targetPct, maxPct];

  function shortDate(iso: string): string {
    const d = new Date(iso);
    return `${(d.getMonth() + 1).toString().padStart(2, "0")}/${d.getDate().toString().padStart(2, "0")}`;
  }

  return (
    <div className="relative w-full">
      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height: CHART_HEIGHT }}
        onMouseLeave={() => setTooltip(null)}
      >
        {/* Y-axis grid + labels */}
        {yTicks.map((tick) => {
          const y = toY(tick);
          return (
            <g key={tick}>
              <line
                x1={PADDING.left}
                x2={VIEWBOX_WIDTH - PADDING.right}
                y1={y}
                y2={y}
                stroke="#e5e7eb"
                strokeWidth={0.25}
              />
              <text
                x={PADDING.left - 2}
                y={y + 1}
                textAnchor="end"
                className="fill-gray-400"
                style={{ fontSize: 2.8 }}
              >
                {tick}%
              </text>
            </g>
          );
        })}

        {/* Threshold dashed line */}
        <line
          x1={PADDING.left}
          x2={VIEWBOX_WIDTH - PADDING.right}
          y1={thresholdY}
          y2={thresholdY}
          stroke={COLOR_FAIL}
          strokeWidth={0.3}
          strokeDasharray="1.5 1"
          opacity={0.6}
        />
        <text
          x={VIEWBOX_WIDTH - PADDING.right + 1}
          y={thresholdY + 1}
          className="fill-red-400"
          style={{ fontSize: 2.4 }}
        >
          {targetPct}%
        </text>

        {/* Line segments */}
        {segments.map((seg, i) => (
          <line
            key={i}
            x1={seg.x1}
            y1={seg.y1}
            x2={seg.x2}
            y2={seg.y2}
            stroke={seg.below ? COLOR_FAIL : COLOR_OK}
            strokeWidth={0.5}
            strokeLinecap="round"
          />
        ))}

        {/* Data dots + invisible hit areas */}
        {points.map((pt, i) => (
          <g key={i}>
            {/* Larger invisible hit area */}
            <circle
              cx={pt.x}
              cy={pt.y}
              r={3}
              fill="transparent"
              className="cursor-pointer"
              onMouseEnter={(e) => {
                const svg = (e.target as SVGElement).closest("svg");
                if (!svg) return;
                const rect = svg.getBoundingClientRect();
                setTooltip({
                  x: rect.left + (pt.x / VIEWBOX_WIDTH) * rect.width,
                  y: rect.top + (pt.y / CHART_HEIGHT) * rect.height - 8,
                  day: pt.day,
                });
              }}
              onMouseLeave={() => setTooltip(null)}
            />
            {/* Visible dot */}
            <circle
              cx={pt.x}
              cy={pt.y}
              r={DOT_RADIUS}
              fill={pt.day.pct < targetPct ? COLOR_FAIL : COLOR_OK}
              className="pointer-events-none"
            />
          </g>
        ))}

        {/* X-axis labels */}
        {data.map((d, i) => (
          <text
            key={d.date}
            x={toX(i)}
            y={CHART_HEIGHT - PADDING.bottom + 8}
            textAnchor="middle"
            className="fill-gray-400"
            style={{ fontSize: 2.6 }}
          >
            {shortDate(d.date)}
          </text>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-1 px-1">
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: COLOR_OK }} />
          Above target
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: COLOR_FAIL }} />
          Below target
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <span className="inline-block w-4 h-0 border-t border-dashed border-red-400" />
          {targetPct}% threshold
        </span>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 rounded-md border border-gray-200 bg-white px-3 py-2 shadow-lg text-xs pointer-events-none"
          style={{ left: tooltip.x, top: tooltip.y, transform: "translate(-50%, -100%)" }}
        >
          <p className="font-semibold text-gray-700">{tooltip.day.date}</p>
          <p className={tooltip.day.pct < targetPct ? "text-red-600" : "text-green-600"}>
            Compliance: {tooltip.day.pct.toFixed(2)}%
          </p>
        </div>
      )}
    </div>
  );
}
