"use client";

import React from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ModelData {
  name: string;
  metrics: Record<string, number>;
}

interface RadarChartProps {
  models: ModelData[];
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const SIZE = 280;
const CENTER = SIZE / 2;
const RADIUS = 100;
const GRID_LEVELS = [0.2, 0.4, 0.6, 0.8, 1.0];
const LABEL_OFFSET = 18;

const PALETTE = [
  "#3b82f6", // blue
  "#ef4444", // red
  "#10b981", // emerald
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#84cc16", // lime
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Compute min/max for each metric across all models, then normalize 0-1. */
function normalizeModels(
  models: ModelData[],
  metricKeys: string[]
): Record<string, number>[] {
  const mins: Record<string, number> = {};
  const maxs: Record<string, number> = {};

  for (const key of metricKeys) {
    let min = Infinity;
    let max = -Infinity;
    for (const m of models) {
      const v = m.metrics[key] ?? 0;
      if (v < min) min = v;
      if (v > max) max = v;
    }
    mins[key] = min;
    maxs[key] = max;
  }

  return models.map((m) => {
    const normalized: Record<string, number> = {};
    for (const key of metricKeys) {
      const range = maxs[key] - mins[key];
      normalized[key] =
        range === 0 ? 1 : (m.metrics[key] ?? 0 - mins[key]) / range;
    }
    return normalized;
  });
}

/** Convert polar (angle + fraction 0-1) to SVG cartesian point. */
function polarToXY(
  angleDeg: number,
  fraction: number
): { x: number; y: number } {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: CENTER + RADIUS * fraction * Math.cos(rad),
    y: CENTER + RADIUS * fraction * Math.sin(rad),
  };
}

function buildPolygonPoints(
  values: Record<string, number>,
  keys: string[],
  step: number
): string {
  return keys
    .map((key, i) => {
      const { x, y } = polarToXY(i * step, values[key] ?? 0);
      return `${x},${y}`;
    })
    .join(" ");
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function RadarChart({ models }: RadarChartProps) {
  if (models.length === 0) return null;

  const metricKeys = Object.keys(models[0].metrics);
  if (metricKeys.length < 3) return null;

  const step = 360 / metricKeys.length;
  const normalized = normalizeModels(models, metricKeys);

  return (
    <div className="flex flex-col items-center">
      <svg
        width={SIZE}
        height={SIZE}
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="select-none"
      >
        {/* Grid rings */}
        {GRID_LEVELS.map((level) => (
          <polygon
            key={level}
            points={metricKeys
              .map((_, i) => {
                const { x, y } = polarToXY(i * step, level);
                return `${x},${y}`;
              })
              .join(" ")}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={0.5}
          />
        ))}

        {/* Percentage labels at grid levels */}
        {GRID_LEVELS.map((level) => {
          const { x, y } = polarToXY(0, level);
          return (
            <text
              key={`pct-${level}`}
              x={x + 2}
              y={y - 2}
              fontSize={8}
              fill="#9ca3af"
            >
              {Math.round(level * 100)}%
            </text>
          );
        })}

        {/* Spokes */}
        {metricKeys.map((_, i) => {
          const { x, y } = polarToXY(i * step, 1);
          return (
            <line
              key={i}
              x1={CENTER}
              y1={CENTER}
              x2={x}
              y2={y}
              stroke="#d1d5db"
              strokeWidth={0.5}
            />
          );
        })}

        {/* Axis labels */}
        {metricKeys.map((key, i) => {
          const { x, y } = polarToXY(
            i * step,
            1 + LABEL_OFFSET / RADIUS
          );
          return (
            <text
              key={key}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={10}
              fontWeight={500}
              fill="#374151"
              className="capitalize"
            >
              {key}
            </text>
          );
        })}

        {/* Model polygons */}
        {normalized.map((values, idx) => (
          <polygon
            key={models[idx].name}
            points={buildPolygonPoints(values, metricKeys, step)}
            fill={PALETTE[idx % PALETTE.length]}
            fillOpacity={0.15}
            stroke={PALETTE[idx % PALETTE.length]}
            strokeWidth={1.5}
          />
        ))}

        {/* Vertex dots */}
        {normalized.map((values, idx) =>
          metricKeys.map((key, i) => {
            const { x, y } = polarToXY(i * step, values[key] ?? 0);
            return (
              <circle
                key={`${models[idx].name}-${key}`}
                cx={x}
                cy={y}
                r={2.5}
                fill={PALETTE[idx % PALETTE.length]}
              />
            );
          })
        )}
      </svg>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap justify-center gap-4 text-xs">
        {models.map((model, idx) => (
          <div key={model.name} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: PALETTE[idx % PALETTE.length] }}
            />
            <span className="text-gray-700">{model.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
