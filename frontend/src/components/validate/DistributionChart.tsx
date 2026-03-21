"use client";

import React, { useMemo } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DistributionChartProps {
  refDistribution: number[];
  curDistribution: number[];
  featureName: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Compute a simple KDE (kernel density estimate) from raw values. */
function kde(
  values: number[],
  gridSize: number,
  bandwidth: number,
): { x: number[]; y: number[] } {
  if (values.length === 0) return { x: [], y: [] };

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = range * 0.1;
  const lo = min - pad;
  const hi = max + pad;
  const step = (hi - lo) / (gridSize - 1);

  const xs: number[] = [];
  const ys: number[] = [];

  for (let i = 0; i < gridSize; i++) {
    const x = lo + i * step;
    xs.push(x);
    let sum = 0;
    for (const v of values) {
      const z = (x - v) / bandwidth;
      sum += Math.exp(-0.5 * z * z);
    }
    ys.push(sum / (values.length * bandwidth * Math.sqrt(2 * Math.PI)));
  }

  return { x: xs, y: ys };
}

function buildPathD(
  xs: number[],
  ys: number[],
  xScale: (v: number) => number,
  yScale: (v: number) => number,
): string {
  if (xs.length === 0) return "";
  const points = xs.map(
    (x, i) => `${xScale(x).toFixed(2)},${yScale(ys[i]).toFixed(2)}`,
  );
  return `M${points.join("L")}`;
}

function buildAreaD(
  xs: number[],
  ys: number[],
  xScale: (v: number) => number,
  yScale: (v: number) => number,
  baseY: number,
): string {
  if (xs.length === 0) return "";
  const top = xs.map(
    (x, i) => `${xScale(x).toFixed(2)},${yScale(ys[i]).toFixed(2)}`,
  );
  const x0 = xScale(xs[0]).toFixed(2);
  const xN = xScale(xs[xs.length - 1]).toFixed(2);
  return `M${x0},${baseY} L${top.join("L")} L${xN},${baseY} Z`;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

const GRID = 80;
const W = 480;
const H = 200;
const PAD = { top: 20, right: 20, bottom: 36, left: 48 };

export default function DistributionChart({
  refDistribution,
  curDistribution,
  featureName,
}: DistributionChartProps) {
  const { refKde, curKde, xMin, xMax, yMax } = useMemo(() => {
    const allVals = [...refDistribution, ...curDistribution];
    if (allVals.length === 0) {
      return {
        refKde: { x: [] as number[], y: [] as number[] },
        curKde: { x: [] as number[], y: [] as number[] },
        xMin: 0,
        xMax: 1,
        yMax: 1,
      };
    }
    const mean = allVals.reduce((a, b) => a + b, 0) / allVals.length;
    const std = Math.sqrt(
      allVals.reduce((s, v) => s + (v - mean) ** 2, 0) / allVals.length,
    );
    const bw = Math.max(std * 0.4, 0.01);
    const r = kde(refDistribution, GRID, bw);
    const c = kde(curDistribution, GRID, bw);
    const allX = [...r.x, ...c.x];
    const allY = [...r.y, ...c.y];
    return {
      refKde: r,
      curKde: c,
      xMin: Math.min(...allX),
      xMax: Math.max(...allX),
      yMax: Math.max(...allY, 0.001),
    };
  }, [refDistribution, curDistribution]);

  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const xScale = (v: number) =>
    PAD.left + ((v - xMin) / (xMax - xMin || 1)) * plotW;
  const yScale = (v: number) => PAD.top + plotH - (v / yMax) * plotH;
  const baseY = PAD.top + plotH;

  const xTicks = Array.from(
    { length: 5 },
    (_, i) => xMin + ((xMax - xMin) / 4) * i,
  );
  const yTicks = Array.from({ length: 4 }, (_, i) => (yMax / 3) * i);

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full max-w-lg mx-auto"
        role="img"
        aria-label={`Distribution chart for ${featureName}`}
      >
        {/* Grid lines */}
        {yTicks.map((t, i) => (
          <line
            key={`yg-${i}`}
            x1={PAD.left}
            x2={W - PAD.right}
            y1={yScale(t)}
            y2={yScale(t)}
            stroke="#e5e7eb"
            strokeWidth={0.5}
          />
        ))}

        {/* Reference area + line */}
        <path
          d={buildAreaD(refKde.x, refKde.y, xScale, yScale, baseY)}
          fill="#3b82f6"
          fillOpacity={0.3}
        />
        <path
          d={buildPathD(refKde.x, refKde.y, xScale, yScale)}
          fill="none"
          stroke="#3b82f6"
          strokeWidth={2}
        />

        {/* Current area + line (dashed) */}
        <path
          d={buildAreaD(curKde.x, curKde.y, xScale, yScale, baseY)}
          fill="#ef4444"
          fillOpacity={0.3}
        />
        <path
          d={buildPathD(curKde.x, curKde.y, xScale, yScale)}
          fill="none"
          stroke="#ef4444"
          strokeWidth={2}
          strokeDasharray="6 3"
        />

        {/* Axes */}
        <line
          x1={PAD.left}
          x2={W - PAD.right}
          y1={baseY}
          y2={baseY}
          stroke="#9ca3af"
          strokeWidth={1}
        />
        <line
          x1={PAD.left}
          x2={PAD.left}
          y1={PAD.top}
          y2={baseY}
          stroke="#9ca3af"
          strokeWidth={1}
        />

        {/* X ticks */}
        {xTicks.map((t, i) => (
          <text
            key={`xt-${i}`}
            x={xScale(t)}
            y={baseY + 14}
            textAnchor="middle"
            className="fill-gray-500"
            fontSize={9}
          >
            {t.toFixed(1)}
          </text>
        ))}

        {/* Y ticks */}
        {yTicks.map((t, i) => (
          <text
            key={`yt-${i}`}
            x={PAD.left - 6}
            y={yScale(t) + 3}
            textAnchor="end"
            className="fill-gray-500"
            fontSize={9}
          >
            {t.toFixed(2)}
          </text>
        ))}

        {/* Axis labels */}
        <text
          x={PAD.left + plotW / 2}
          y={H - 2}
          textAnchor="middle"
          className="fill-gray-600"
          fontSize={10}
        >
          Value Range
        </text>
        <text
          x={10}
          y={PAD.top + plotH / 2}
          textAnchor="middle"
          className="fill-gray-600"
          fontSize={10}
          transform={`rotate(-90, 10, ${PAD.top + plotH / 2})`}
        >
          Density
        </text>

        {/* Legend */}
        <rect
          x={W - PAD.right - 120}
          y={PAD.top}
          width={10}
          height={10}
          fill="#3b82f6"
          fillOpacity={0.6}
          rx={2}
        />
        <text
          x={W - PAD.right - 106}
          y={PAD.top + 9}
          className="fill-gray-700"
          fontSize={9}
        >
          Reference
        </text>
        <rect
          x={W - PAD.right - 120}
          y={PAD.top + 16}
          width={10}
          height={10}
          fill="#ef4444"
          fillOpacity={0.6}
          rx={2}
        />
        <text
          x={W - PAD.right - 106}
          y={PAD.top + 25}
          className="fill-gray-700"
          fontSize={9}
        >
          Current
        </text>
      </svg>
    </div>
  );
}
