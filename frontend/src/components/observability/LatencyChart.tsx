"use client";

import { useState } from "react";

// ----------------------------------------------------------------
// Types
// ----------------------------------------------------------------

export interface LatencyDataPoint {
  timestamp: string;
  avg_ms: number;
  p99_ms: number;
}

export interface LatencyChartProps {
  data: LatencyDataPoint[];
  slaTargetMs: number;
}

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------

const PADDING = { top: 20, right: 16, bottom: 32, left: 48 };
const CHART_HEIGHT = 200;

function formatTime(iso: string): string {
  const d = new Date(iso);
  return `${d.getHours().toString().padStart(2, "0")}:${d
    .getMinutes()
    .toString()
    .padStart(2, "0")}`;
}

function buildPath(
  points: { x: number; y: number }[],
): string {
  return points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
}

// ----------------------------------------------------------------
// Component
// ----------------------------------------------------------------

export default function LatencyChart({ data, slaTargetMs }: LatencyChartProps) {
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    point: LatencyDataPoint;
  } | null>(null);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-gray-400 text-sm">
        No latency data available.
      </div>
    );
  }

  // Compute scale
  const allValues = data.flatMap((d) => [d.avg_ms, d.p99_ms, slaTargetMs]);
  const maxY = Math.max(...allValues) * 1.15; // 15% headroom
  const minY = 0;

  // Inner dimensions — use a stable width; SVG viewBox handles responsiveness
  const SVG_WIDTH = 800;
  const innerW = SVG_WIDTH - PADDING.left - PADDING.right;
  const innerH = CHART_HEIGHT - PADDING.top - PADDING.bottom;

  const xScale = (i: number) =>
    PADDING.left + (i / Math.max(data.length - 1, 1)) * innerW;
  const yScale = (v: number) =>
    PADDING.top + innerH - ((v - minY) / (maxY - minY)) * innerH;

  const avgPoints = data.map((d, i) => ({ x: xScale(i), y: yScale(d.avg_ms) }));
  const p99Points = data.map((d, i) => ({ x: xScale(i), y: yScale(d.p99_ms) }));

  const slaY = yScale(slaTargetMs);

  // X-axis labels: show ~6 evenly spaced labels
  const labelCount = Math.min(6, data.length);
  const labelStep = Math.max(1, Math.floor((data.length - 1) / (labelCount - 1)));
  const xLabels: { idx: number; label: string; x: number }[] = [];
  for (let i = 0; i < data.length; i += labelStep) {
    xLabels.push({ idx: i, label: formatTime(data[i].timestamp), x: xScale(i) });
  }
  // Always include last point
  if (xLabels[xLabels.length - 1]?.idx !== data.length - 1) {
    xLabels.push({
      idx: data.length - 1,
      label: formatTime(data[data.length - 1].timestamp),
      x: xScale(data.length - 1),
    });
  }

  // Y-axis ticks: 5 ticks
  const yTicks: { value: number; y: number }[] = [];
  for (let i = 0; i <= 4; i++) {
    const v = minY + ((maxY - minY) * i) / 4;
    yTicks.push({ value: Math.round(v), y: yScale(v) });
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wide">
        Latency Over Time
      </h3>

      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${CHART_HEIGHT}`}
        className="w-full"
        style={{ height: CHART_HEIGHT }}
        onMouseLeave={() => setTooltip(null)}
      >
        {/* Grid lines */}
        {yTicks.map((t) => (
          <line
            key={t.value}
            x1={PADDING.left}
            y1={t.y}
            x2={SVG_WIDTH - PADDING.right}
            y2={t.y}
            stroke="#e5e7eb"
            strokeWidth={1}
          />
        ))}

        {/* Y-axis labels */}
        {yTicks.map((t) => (
          <text
            key={`yl-${t.value}`}
            x={PADDING.left - 6}
            y={t.y + 4}
            textAnchor="end"
            className="fill-gray-400"
            fontSize={10}
          >
            {t.value}ms
          </text>
        ))}

        {/* X-axis labels */}
        {xLabels.map((l) => (
          <text
            key={`xl-${l.idx}`}
            x={l.x}
            y={CHART_HEIGHT - 6}
            textAnchor="middle"
            className="fill-gray-400"
            fontSize={10}
          >
            {l.label}
          </text>
        ))}

        {/* SLA threshold line */}
        <line
          x1={PADDING.left}
          y1={slaY}
          x2={SVG_WIDTH - PADDING.right}
          y2={slaY}
          stroke="#ef4444"
          strokeWidth={1.5}
          strokeDasharray="6 4"
        />
        <text
          x={SVG_WIDTH - PADDING.right + 4}
          y={slaY + 3}
          className="fill-red-500"
          fontSize={9}
          fontWeight={600}
        >
          SLA
        </text>

        {/* Avg latency line (blue solid) */}
        <path
          d={buildPath(avgPoints)}
          fill="none"
          stroke="#3b82f6"
          strokeWidth={2}
        />

        {/* P99 latency line (amber dashed) */}
        <path
          d={buildPath(p99Points)}
          fill="none"
          stroke="#f59e0b"
          strokeWidth={2}
          strokeDasharray="6 3"
        />

        {/* Invisible hit areas for tooltips */}
        {data.map((d, i) => (
          <circle
            key={i}
            cx={xScale(i)}
            cy={yScale(d.avg_ms)}
            r={12}
            fill="transparent"
            onMouseEnter={() =>
              setTooltip({ x: xScale(i), y: yScale(d.avg_ms), point: d })
            }
          />
        ))}

        {/* Visible data dots on hover */}
        {tooltip && (
          <>
            <circle cx={tooltip.x} cy={tooltip.y} r={4} fill="#3b82f6" />
            <circle
              cx={tooltip.x}
              cy={yScale(tooltip.point.p99_ms)}
              r={4}
              fill="#f59e0b"
            />
          </>
        )}
      </svg>

      {/* Tooltip overlay */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded bg-gray-900 px-3 py-2 text-xs text-white shadow-lg"
          style={{
            left: `${(tooltip.x / SVG_WIDTH) * 100}%`,
            transform: "translateX(-50%)",
            marginTop: -CHART_HEIGHT - 8,
          }}
        >
          <p className="font-medium">{formatTime(tooltip.point.timestamp)}</p>
          <p>
            <span className="text-blue-300">Avg:</span> {tooltip.point.avg_ms.toFixed(1)}ms
          </p>
          <p>
            <span className="text-amber-300">p99:</span> {tooltip.point.p99_ms.toFixed(1)}ms
          </p>
        </div>
      )}

      {/* Legend */}
      <div className="mt-3 flex items-center gap-5 text-xs text-gray-600">
        <div className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-5 bg-blue-500" />
          <span>Avg latency</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block h-0.5 w-5 bg-amber-500"
            style={{ backgroundImage: "repeating-linear-gradient(90deg, #f59e0b 0 4px, transparent 4px 7px)" }}
          />
          <span>p99 latency</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block h-0.5 w-5 bg-red-500"
            style={{ backgroundImage: "repeating-linear-gradient(90deg, #ef4444 0 4px, transparent 4px 7px)" }}
          />
          <span>SLA threshold ({slaTargetMs}ms)</span>
        </div>
      </div>
    </div>
  );
}
