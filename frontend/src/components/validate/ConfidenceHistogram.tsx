"use client";

import React from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CalibrationBin {
  bin_start: number;
  bin_end: number;
  avg_confidence: number;
  accuracy: number;
  count: number;
}

interface ConfidenceHistogramProps {
  bins: CalibrationBin[];
  /** Decision threshold (vertical dashed line). Defaults to 0.5. */
  threshold?: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const WIDTH = 400;
const HEIGHT = 200;
const PADDING_LEFT = 45;
const PADDING_RIGHT = 15;
const PADDING_TOP = 15;
const PADDING_BOTTOM = 30;
const PLOT_W = WIDTH - PADDING_LEFT - PADDING_RIGHT;
const PLOT_H = HEIGHT - PADDING_TOP - PADDING_BOTTOM;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ConfidenceHistogram({
  bins,
  threshold = 0.5,
}: ConfidenceHistogramProps) {
  const maxCount = Math.max(...bins.map((b) => b.count), 1);

  // Compute mean confidence weighted by count
  const totalCount = bins.reduce((s, b) => s + b.count, 0);
  const meanConfidence =
    totalCount > 0
      ? bins.reduce((s, b) => s + b.avg_confidence * b.count, 0) / totalCount
      : 0.5;

  // Build area-chart points
  const points: string[] = [];
  bins.forEach((bin, i) => {
    const xStart = PADDING_LEFT + (bin.bin_start * PLOT_W);
    const xEnd = PADDING_LEFT + (bin.bin_end * PLOT_W);
    const y = PADDING_TOP + PLOT_H - (bin.count / maxCount) * PLOT_H;
    if (i === 0) {
      points.push(`${xStart},${PADDING_TOP + PLOT_H}`);
    }
    points.push(`${xStart},${y}`);
    points.push(`${xEnd},${y}`);
    if (i === bins.length - 1) {
      points.push(`${xEnd},${PADDING_TOP + PLOT_H}`);
    }
  });

  const xForValue = (v: number) => PADDING_LEFT + v * PLOT_W;

  return (
    <figure className="flex flex-col items-center">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        width={WIDTH}
        height={HEIGHT}
        className="overflow-visible"
        aria-label="Confidence Histogram"
      >
        {/* Axes */}
        <line
          x1={PADDING_LEFT}
          y1={PADDING_TOP}
          x2={PADDING_LEFT}
          y2={PADDING_TOP + PLOT_H}
          stroke="#9ca3af"
          strokeWidth={1}
        />
        <line
          x1={PADDING_LEFT}
          y1={PADDING_TOP + PLOT_H}
          x2={PADDING_LEFT + PLOT_W}
          y2={PADDING_TOP + PLOT_H}
          stroke="#9ca3af"
          strokeWidth={1}
        />

        {/* X-axis ticks */}
        {Array.from({ length: 6 }).map((_, i) => {
          const frac = i / 5;
          const x = PADDING_LEFT + frac * PLOT_W;
          return (
            <text
              key={`x${i}`}
              x={x}
              y={PADDING_TOP + PLOT_H + 14}
              textAnchor="middle"
              fontSize={9}
              fill="#6b7280"
            >
              {frac.toFixed(1)}
            </text>
          );
        })}

        {/* Y-axis ticks */}
        {[0, 0.5, 1].map((frac) => {
          const y = PADDING_TOP + PLOT_H - frac * PLOT_H;
          const label = Math.round(frac * maxCount);
          return (
            <text
              key={`y${frac}`}
              x={PADDING_LEFT - 6}
              y={y + 3}
              textAnchor="end"
              fontSize={9}
              fill="#6b7280"
            >
              {label}
            </text>
          );
        })}

        {/* Axis labels */}
        <text
          x={PADDING_LEFT + PLOT_W / 2}
          y={HEIGHT - 2}
          textAnchor="middle"
          fontSize={10}
          fill="#374151"
        >
          Confidence
        </text>
        <text
          x={8}
          y={PADDING_TOP + PLOT_H / 2}
          textAnchor="middle"
          fontSize={10}
          fill="#374151"
          transform={`rotate(-90, 8, ${PADDING_TOP + PLOT_H / 2})`}
        >
          Frequency
        </text>

        {/* Filled area chart */}
        <polygon
          points={points.join(" ")}
          fill="#3b82f6"
          fillOpacity={0.35}
          stroke="#3b82f6"
          strokeWidth={1.5}
        />

        {/* Mean confidence dashed line */}
        <line
          x1={xForValue(meanConfidence)}
          y1={PADDING_TOP}
          x2={xForValue(meanConfidence)}
          y2={PADDING_TOP + PLOT_H}
          stroke="#f59e0b"
          strokeWidth={1}
          strokeDasharray="4 3"
        />
        <text
          x={xForValue(meanConfidence) + 3}
          y={PADDING_TOP + 10}
          fontSize={8}
          fill="#f59e0b"
        >
          mean ({meanConfidence.toFixed(2)})
        </text>

        {/* Threshold dashed line */}
        <line
          x1={xForValue(threshold)}
          y1={PADDING_TOP}
          x2={xForValue(threshold)}
          y2={PADDING_TOP + PLOT_H}
          stroke="#ef4444"
          strokeWidth={1}
          strokeDasharray="4 3"
        />
        <text
          x={xForValue(threshold) - 3}
          y={PADDING_TOP + 20}
          fontSize={8}
          fill="#ef4444"
          textAnchor="end"
        >
          threshold ({threshold.toFixed(2)})
        </text>
      </svg>
      <figcaption className="mt-2 text-xs text-gray-500 text-center max-w-sm">
        Distribution of prediction confidence scores. The amber dashed line marks
        mean confidence; the red dashed line marks the decision threshold.
      </figcaption>
    </figure>
  );
}
