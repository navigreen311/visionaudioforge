"use client";

import React, { useMemo, useState, useId } from "react";
import type { RoundData } from "./types";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface AccuracyLossChartProps {
  rounds: RoundData[];
  /** Target accuracy percentage (0-100). Defaults to 90. */
  targetAccuracy?: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const SVG_WIDTH = 600;
const SVG_HEIGHT = 240;
const PAD_LEFT = 52;
const PAD_RIGHT = 52;
const PAD_TOP = 20;
const PAD_BOTTOM = 28;
const DRAW_W = SVG_WIDTH - PAD_LEFT - PAD_RIGHT;
const DRAW_H = SVG_HEIGHT - PAD_TOP - PAD_BOTTOM;

const ACC_COLOR = "#2563EB"; // blue-600
const LOSS_COLOR = "#DC2626"; // red-600
const TARGET_COLOR = "#9CA3AF"; // gray-400

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

interface Point {
  x: number;
  y: number;
  value: number;
  round: number;
}

function scaleX(index: number, count: number): number {
  if (count <= 1) return PAD_LEFT;
  return PAD_LEFT + (index / (count - 1)) * DRAW_W;
}

function scaleY(value: number, min: number, range: number): number {
  return PAD_TOP + DRAW_H - ((value - min) / (range || 1)) * DRAW_H;
}

function toPath(pts: Point[]): string {
  return pts
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(" ");
}

function formatValue(v: number, isPercent: boolean): string {
  return isPercent ? `${v.toFixed(1)}%` : v.toFixed(4);
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function AccuracyLossChart({
  rounds,
  targetAccuracy = 90,
}: AccuracyLossChartProps) {
  const uid = useId();
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const computed = useMemo(() => {
    if (rounds.length === 0) return null;

    const count = rounds.length;

    // Accuracy: 0-100 fixed range
    const accMin = 0;
    const accMax = 100;
    const accRange = accMax - accMin;

    // Loss: dynamic range with padding
    const lossVals = rounds.map((r) => r.loss).filter((v): v is number => v !== null);
    const lossMin = lossVals.length > 0 ? Math.min(...lossVals) * 0.9 : 0;
    const lossMax = lossVals.length > 0 ? Math.max(...lossVals) * 1.1 : 1;
    const lossRange = lossMax - lossMin;

    const accPoints: Point[] = [];
    const lossPoints: Point[] = [];

    for (let i = 0; i < count; i++) {
      const r = rounds[i];
      const x = scaleX(i, count);

      if (r.accuracy !== null) {
        accPoints.push({
          x,
          y: scaleY(r.accuracy, accMin, accRange),
          value: r.accuracy,
          round: r.round_number,
        });
      }
      if (r.loss !== null) {
        lossPoints.push({
          x,
          y: scaleY(r.loss, lossMin, lossRange),
          value: r.loss,
          round: r.round_number,
        });
      }
    }

    // Target accuracy line Y position
    const targetY = scaleY(targetAccuracy, accMin, accRange);

    // Y-axis ticks for accuracy (left)
    const accTicks = [0, 25, 50, 75, 100];

    // Y-axis ticks for loss (right, 5 ticks)
    const lossTicks = Array.from({ length: 5 }, (_, i) => lossMin + (lossRange * i) / 4);

    return { accPoints, lossPoints, targetY, accTicks, lossTicks, lossMin, lossRange, accMin, accRange, count };
  }, [rounds, targetAccuracy]);

  if (!computed || rounds.length === 0) {
    return (
      <div className="flex items-center justify-center h-[240px] text-sm text-gray-400">
        No round data yet
      </div>
    );
  }

  const { accPoints, lossPoints, targetY, accTicks, lossTicks, lossMin, lossRange, accMin, accRange, count } = computed;

  // Tooltip data
  const hovered = hoveredIdx !== null ? rounds[hoveredIdx] : null;

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        className="w-full"
        style={{ height: SVG_HEIGHT }}
        preserveAspectRatio="none"
        role="img"
        aria-label="Accuracy and Loss chart"
      >
        <defs>
          <linearGradient id={`${uid}-acc-fill`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={ACC_COLOR} stopOpacity={0.1} />
            <stop offset="100%" stopColor={ACC_COLOR} stopOpacity={0} />
          </linearGradient>
        </defs>

        {/* Left Y-axis grid + labels (Accuracy) */}
        {accTicks.map((tick) => {
          const y = scaleY(tick, accMin, accRange);
          return (
            <g key={`acc-${tick}`}>
              <line x1={PAD_LEFT} y1={y} x2={SVG_WIDTH - PAD_RIGHT} y2={y} stroke="#E5E7EB" strokeWidth={0.5} />
              <text x={PAD_LEFT - 6} y={y + 3} textAnchor="end" fill="#6B7280" className="text-[9px]">
                {tick}%
              </text>
            </g>
          );
        })}

        {/* Right Y-axis labels (Loss) */}
        {lossTicks.map((tick) => {
          const y = scaleY(tick, lossMin, lossRange);
          return (
            <text
              key={`loss-${tick}`}
              x={SVG_WIDTH - PAD_RIGHT + 6}
              y={y + 3}
              textAnchor="start"
              fill="#9CA3AF"
              className="text-[9px]"
            >
              {tick.toFixed(3)}
            </text>
          );
        })}

        {/* Target accuracy dashed line */}
        <line
          x1={PAD_LEFT}
          y1={targetY}
          x2={SVG_WIDTH - PAD_RIGHT}
          y2={targetY}
          stroke={TARGET_COLOR}
          strokeWidth={1}
          strokeDasharray="6 4"
          opacity={0.7}
        />
        <text
          x={SVG_WIDTH - PAD_RIGHT - 2}
          y={targetY - 4}
          textAnchor="end"
          fill={TARGET_COLOR}
          className="text-[8px]"
        >
          Target {targetAccuracy}%
        </text>

        {/* Accuracy area fill */}
        {accPoints.length > 1 && (
          <path
            d={`${toPath(accPoints)} L ${accPoints[accPoints.length - 1].x.toFixed(1)},${(PAD_TOP + DRAW_H).toFixed(1)} L ${accPoints[0].x.toFixed(1)},${(PAD_TOP + DRAW_H).toFixed(1)} Z`}
            fill={`url(#${uid}-acc-fill)`}
          />
        )}

        {/* Accuracy line (solid) */}
        <path
          d={toPath(accPoints)}
          fill="none"
          stroke={ACC_COLOR}
          strokeWidth={2}
          strokeLinejoin="round"
        >
          <animate
            attributeName="stroke-dashoffset"
            from="2000"
            to="0"
            dur="1s"
            fill="freeze"
          />
          <set attributeName="stroke-dasharray" to="2000" />
        </path>

        {/* Loss line (dashed) */}
        <path
          d={toPath(lossPoints)}
          fill="none"
          stroke={LOSS_COLOR}
          strokeWidth={2}
          strokeLinejoin="round"
          strokeDasharray="6 3"
        />

        {/* Accuracy dots (circles) */}
        {accPoints.map((p, i) => (
          <circle
            key={`acc-dot-${i}`}
            cx={p.x}
            cy={p.y}
            r={hoveredIdx === rounds.findIndex((r) => r.round_number === p.round) ? 5 : 3}
            fill={ACC_COLOR}
            className="transition-all duration-150"
          />
        ))}

        {/* Loss dots (squares via rect) */}
        {lossPoints.map((p, i) => {
          const size = hoveredIdx === rounds.findIndex((r) => r.round_number === p.round) ? 10 : 6;
          return (
            <rect
              key={`loss-dot-${i}`}
              x={p.x - size / 2}
              y={p.y - size / 2}
              width={size}
              height={size}
              fill={LOSS_COLOR}
              className="transition-all duration-150"
            />
          );
        })}

        {/* X-axis labels */}
        {rounds
          .filter((_, i) => {
            if (count <= 12) return true;
            const every = Math.ceil(count / 12);
            return i % every === 0 || i === count - 1;
          })
          .map((r) => {
            const idx = rounds.indexOf(r);
            const x = scaleX(idx, count);
            return (
              <text
                key={`x-${r.round_number}`}
                x={x}
                y={SVG_HEIGHT - 6}
                textAnchor="middle"
                fill="#9CA3AF"
                className="text-[9px]"
              >
                R{r.round_number}
              </text>
            );
          })}

        {/* Hover regions */}
        {rounds.map((_, i) => {
          const x = scaleX(i, count);
          const regionW = count > 1 ? DRAW_W / (count - 1) : DRAW_W;
          return (
            <rect
              key={`hover-${i}`}
              x={x - regionW / 2}
              y={PAD_TOP}
              width={regionW}
              height={DRAW_H}
              fill="transparent"
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
            />
          );
        })}

        {/* Hover vertical line */}
        {hoveredIdx !== null && (
          <line
            x1={scaleX(hoveredIdx, count)}
            y1={PAD_TOP}
            x2={scaleX(hoveredIdx, count)}
            y2={PAD_TOP + DRAW_H}
            stroke="#6B7280"
            strokeWidth={1}
            strokeDasharray="3 2"
            opacity={0.5}
          />
        )}
      </svg>

      {/* Tooltip */}
      {hovered && hoveredIdx !== null && (
        <div
          className="absolute z-10 bg-gray-900 text-white text-xs rounded-md px-3 py-2 shadow-lg pointer-events-none"
          style={{
            left: `${(scaleX(hoveredIdx, count) / SVG_WIDTH) * 100}%`,
            top: 4,
            transform: hoveredIdx > count / 2 ? "translateX(-100%)" : "translateX(0)",
          }}
        >
          <div className="font-semibold mb-1">Round {hovered.round_number}</div>
          {hovered.accuracy !== null && (
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: ACC_COLOR }} />
              Accuracy: {formatValue(hovered.accuracy, true)}
            </div>
          )}
          {hovered.loss !== null && (
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2" style={{ backgroundColor: LOSS_COLOR }} />
              Loss: {formatValue(hovered.loss, false)}
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-2">
        <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-500">
          <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: ACC_COLOR }} />
          Accuracy
        </span>
        <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-500">
          <span className="inline-block h-2 w-2" style={{ backgroundColor: LOSS_COLOR }} />
          Loss
        </span>
        <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-500">
          <span className="inline-block h-0.5 w-3 border-t border-dashed" style={{ borderColor: TARGET_COLOR }} />
          Target {targetAccuracy}%
        </span>
      </div>
    </div>
  );
}
