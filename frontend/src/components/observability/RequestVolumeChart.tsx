"use client";

import React, { useState } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface HourlyBucket {
  hour: number;       // 0-23
  success: number;
  errors: number;
}

interface TooltipState {
  x: number;
  y: number;
  bucket: HourlyBucket;
}

interface RequestVolumeChartProps {
  data: HourlyBucket[];
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const CHART_HEIGHT = 180;
const PADDING = { top: 16, right: 12, bottom: 28, left: 42 };
const BAR_GAP = 2;
const COLOR_SUCCESS = "#3b82f6"; // blue-500
const COLOR_ERROR = "#ef4444";   // red-500
const COLOR_HIGHLIGHT = "rgba(59,130,246,0.12)";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function RequestVolumeChart({ data }: RequestVolumeChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const currentHour = new Date().getHours();

  // Normalise to 24 buckets, filling gaps with zeroes
  const buckets: HourlyBucket[] = Array.from({ length: 24 }, (_, i) => {
    const found = data.find((d) => d.hour === i);
    return found ?? { hour: i, success: 0, errors: 0 };
  });

  const maxTotal = Math.max(...buckets.map((b) => b.success + b.errors), 1);

  // Derived layout
  const innerWidth = 100; // percent-based via viewBox
  const usableWidth = innerWidth - PADDING.left - PADDING.right;
  const usableHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
  const barWidth = (usableWidth - BAR_GAP * 23) / 24;

  // Y-axis ticks (3 evenly spaced)
  const yTicks = [0, Math.round(maxTotal / 2), maxTotal];

  function formatHour(h: number): string {
    return `${h.toString().padStart(2, "0")}`;
  }

  return (
    <div className="relative w-full">
      <svg
        viewBox={`0 0 ${innerWidth} ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height: CHART_HEIGHT }}
        onMouseLeave={() => setTooltip(null)}
      >
        {/* Y-axis grid lines + labels */}
        {yTicks.map((tick) => {
          const y = PADDING.top + usableHeight - (tick / maxTotal) * usableHeight;
          return (
            <g key={tick}>
              <line
                x1={PADDING.left}
                x2={innerWidth - PADDING.right}
                y1={y}
                y2={y}
                stroke="#e5e7eb"
                strokeWidth={0.3}
              />
              <text
                x={PADDING.left - 2}
                y={y + 1.2}
                textAnchor="end"
                className="fill-gray-400"
                style={{ fontSize: 3.2 }}
              >
                {tick}
              </text>
            </g>
          );
        })}

        {/* Bars */}
        {buckets.map((bucket, i) => {
          const total = bucket.success + bucket.errors;
          const x = PADDING.left + i * (barWidth + BAR_GAP);
          const totalH = (total / maxTotal) * usableHeight;
          const errH = (bucket.errors / maxTotal) * usableHeight;
          const barY = PADDING.top + usableHeight - totalH;
          const isCurrent = bucket.hour === currentHour;

          return (
            <g
              key={bucket.hour}
              onMouseEnter={(e) => {
                const svg = (e.target as SVGElement).closest("svg");
                if (!svg) return;
                const rect = svg.getBoundingClientRect();
                setTooltip({
                  x: rect.left + (x / innerWidth) * rect.width + (barWidth / innerWidth) * rect.width / 2,
                  y: rect.top + (barY / CHART_HEIGHT) * rect.height - 8,
                  bucket,
                });
              }}
              onMouseLeave={() => setTooltip(null)}
              className="cursor-pointer"
            >
              {/* Highlight background for current hour */}
              {isCurrent && (
                <rect
                  x={x - 0.5}
                  y={PADDING.top}
                  width={barWidth + 1}
                  height={usableHeight}
                  fill={COLOR_HIGHLIGHT}
                  rx={0.4}
                />
              )}

              {/* Success portion */}
              <rect
                x={x}
                y={barY}
                width={barWidth}
                height={Math.max(totalH - errH, 0)}
                fill={COLOR_SUCCESS}
                rx={0.3}
              />

              {/* Error portion (stacked on top) */}
              {bucket.errors > 0 && (
                <rect
                  x={x}
                  y={PADDING.top + usableHeight - errH}
                  width={barWidth}
                  height={errH}
                  fill={COLOR_ERROR}
                  rx={0.3}
                />
              )}

              {/* X-axis label (show every 3 hours to avoid clutter) */}
              {bucket.hour % 3 === 0 && (
                <text
                  x={x + barWidth / 2}
                  y={CHART_HEIGHT - PADDING.bottom + 8}
                  textAnchor="middle"
                  className="fill-gray-400"
                  style={{ fontSize: 3 }}
                >
                  {formatHour(bucket.hour)}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-1 px-1">
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: COLOR_SUCCESS }} />
          Success
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: COLOR_ERROR }} />
          Errors
        </span>
      </div>

      {/* Tooltip (portal-style, positioned via fixed coords) */}
      {tooltip && (
        <div
          className="fixed z-50 rounded-md border border-gray-200 bg-white px-3 py-2 shadow-lg text-xs pointer-events-none"
          style={{ left: tooltip.x, top: tooltip.y, transform: "translate(-50%, -100%)" }}
        >
          <p className="font-semibold text-gray-700">{formatHour(tooltip.bucket.hour)}:00</p>
          <p className="text-blue-600">Success: {tooltip.bucket.success}</p>
          <p className="text-red-500">Errors: {tooltip.bucket.errors}</p>
          <p className="text-gray-500">
            Total: {tooltip.bucket.success + tooltip.bucket.errors}
          </p>
        </div>
      )}
    </div>
  );
}
