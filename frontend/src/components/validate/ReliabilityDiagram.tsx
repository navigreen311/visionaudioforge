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

interface ReliabilityDiagramProps {
  bins: CalibrationBin[];
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const WIDTH = 300;
const HEIGHT = 300;
const PADDING = 40;
const PLOT_W = WIDTH - PADDING * 2;
const PLOT_H = HEIGHT - PADDING * 2;
const N_TICKS = 5;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ReliabilityDiagram({ bins }: ReliabilityDiagramProps) {
  const barWidth = PLOT_W / bins.length;

  return (
    <figure className="flex flex-col items-center">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        width={WIDTH}
        height={HEIGHT}
        className="overflow-visible"
        aria-label="Reliability Diagram"
      >
        {/* Axes */}
        <line
          x1={PADDING}
          y1={PADDING}
          x2={PADDING}
          y2={PADDING + PLOT_H}
          stroke="#9ca3af"
          strokeWidth={1}
        />
        <line
          x1={PADDING}
          y1={PADDING + PLOT_H}
          x2={PADDING + PLOT_W}
          y2={PADDING + PLOT_H}
          stroke="#9ca3af"
          strokeWidth={1}
        />

        {/* Tick labels */}
        {Array.from({ length: N_TICKS + 1 }).map((_, i) => {
          const frac = i / N_TICKS;
          const label = frac.toFixed(1);
          const xPos = PADDING + frac * PLOT_W;
          const yPos = PADDING + PLOT_H - frac * PLOT_H;
          return (
            <g key={i}>
              {/* X-axis tick */}
              <text
                x={xPos}
                y={PADDING + PLOT_H + 14}
                textAnchor="middle"
                fontSize={9}
                fill="#6b7280"
              >
                {label}
              </text>
              {/* Y-axis tick */}
              <text
                x={PADDING - 6}
                y={yPos + 3}
                textAnchor="end"
                fontSize={9}
                fill="#6b7280"
              >
                {label}
              </text>
            </g>
          );
        })}

        {/* Axis labels */}
        <text
          x={PADDING + PLOT_W / 2}
          y={HEIGHT - 2}
          textAnchor="middle"
          fontSize={10}
          fill="#374151"
        >
          Mean Predicted Probability
        </text>
        <text
          x={10}
          y={PADDING + PLOT_H / 2}
          textAnchor="middle"
          fontSize={10}
          fill="#374151"
          transform={`rotate(-90, 10, ${PADDING + PLOT_H / 2})`}
        >
          Fraction of Positives
        </text>

        {/* Perfect calibration line (dashed diagonal) */}
        <line
          x1={PADDING}
          y1={PADDING + PLOT_H}
          x2={PADDING + PLOT_W}
          y2={PADDING}
          stroke="#6b7280"
          strokeWidth={1}
          strokeDasharray="4 3"
        />

        {/* Bars per bin */}
        {bins.map((bin, i) => {
          const barH = bin.accuracy * PLOT_H;
          const x = PADDING + i * barWidth;
          const y = PADDING + PLOT_H - barH;
          return (
            <rect
              key={i}
              x={x + 1}
              y={y}
              width={Math.max(barWidth - 2, 1)}
              height={barH}
              fill="#3b82f6"
              opacity={0.75}
            >
              <title>
                {`Bin ${bin.bin_start.toFixed(1)}-${bin.bin_end.toFixed(1)}: accuracy=${bin.accuracy.toFixed(3)}, count=${bin.count}`}
              </title>
            </rect>
          );
        })}
      </svg>
      <figcaption className="mt-2 text-xs text-gray-500 text-center max-w-xs">
        Reliability diagram comparing predicted probability (x-axis) to observed
        fraction of positives (y-axis). The dashed line represents perfect
        calibration.
      </figcaption>
    </figure>
  );
}
