"use client";

import React, { useMemo, useId } from "react";
import type { RoundData } from "./types";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface PrivacyBudgetChartProps {
  rounds: RoundData[];
  /** Maximum epsilon budget. */
  maxEpsilon: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const SVG_WIDTH = 600;
const SVG_HEIGHT = 80;
const PAD_LEFT = 40;
const PAD_RIGHT = 12;
const PAD_TOP = 8;
const PAD_BOTTOM = 16;
const DRAW_W = SVG_WIDTH - PAD_LEFT - PAD_RIGHT;
const DRAW_H = SVG_HEIGHT - PAD_TOP - PAD_BOTTOM;

const COLOR_NORMAL = "#2563EB"; // blue-600
const COLOR_AMBER = "#D97706"; // amber-600
const COLOR_RED = "#DC2626"; // red-600
const FILL_NORMAL = "#DBEAFE"; // blue-100
const FILL_AMBER = "#FEF3C7"; // amber-100
const FILL_RED = "#FEE2E2"; // red-100

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

interface Point {
  x: number;
  y: number;
}

function scaleX(index: number, count: number): number {
  if (count <= 1) return PAD_LEFT;
  return PAD_LEFT + (index / (count - 1)) * DRAW_W;
}

function scaleY(value: number, max: number): number {
  return PAD_TOP + DRAW_H - (value / (max || 1)) * DRAW_H;
}

function getColor(ratio: number): { stroke: string; fill: string } {
  if (ratio > 0.9) return { stroke: COLOR_RED, fill: FILL_RED };
  if (ratio > 0.7) return { stroke: COLOR_AMBER, fill: FILL_AMBER };
  return { stroke: COLOR_NORMAL, fill: FILL_NORMAL };
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function PrivacyBudgetChart({ rounds, maxEpsilon }: PrivacyBudgetChartProps) {
  const uid = useId();

  const computed = useMemo(() => {
    if (rounds.length === 0 || maxEpsilon <= 0) return null;

    const count = rounds.length;

    // Build cumulative epsilon
    let cumulative = 0;
    const cumulativeValues: number[] = [];
    for (const r of rounds) {
      cumulative += r.privacy_epsilon_spent;
      cumulativeValues.push(cumulative);
    }

    const currentTotal = cumulativeValues[cumulativeValues.length - 1];
    const ratio = currentTotal / maxEpsilon;
    const { stroke, fill } = getColor(ratio);

    // Points
    const points: Point[] = cumulativeValues.map((val, i) => ({
      x: scaleX(i, count),
      y: scaleY(val, maxEpsilon),
    }));

    // Path
    const linePath = points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)},${p.y.toFixed(1)}`)
      .join(" ");

    // Area path
    const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)},${(PAD_TOP + DRAW_H).toFixed(1)} L ${points[0].x.toFixed(1)},${(PAD_TOP + DRAW_H).toFixed(1)} Z`;

    // Budget exhausted estimate
    const avgPerRound = currentTotal / count;
    const remaining = maxEpsilon - currentTotal;
    const roundsRemaining = avgPerRound > 0 ? Math.ceil(remaining / avgPerRound) : Infinity;

    // Max budget line Y
    const budgetLineY = scaleY(maxEpsilon, maxEpsilon); // should be PAD_TOP

    return {
      linePath,
      areaPath,
      stroke,
      fill,
      budgetLineY,
      currentTotal,
      roundsRemaining,
      ratio,
      count,
    };
  }, [rounds, maxEpsilon]);

  if (!computed) {
    return (
      <div className="flex items-center justify-center h-[80px] text-xs text-gray-400">
        No privacy data
      </div>
    );
  }

  const { linePath, areaPath, stroke, fill, budgetLineY, currentTotal, roundsRemaining, ratio, count } = computed;

  return (
    <div>
      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        className="w-full"
        style={{ height: SVG_HEIGHT }}
        preserveAspectRatio="none"
        role="img"
        aria-label="Privacy budget chart"
      >
        <defs>
          <linearGradient id={`${uid}-budget-fill`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={fill} stopOpacity={0.8} />
            <stop offset="100%" stopColor={fill} stopOpacity={0.2} />
          </linearGradient>
        </defs>

        {/* Max budget dashed line */}
        <line
          x1={PAD_LEFT}
          y1={budgetLineY}
          x2={SVG_WIDTH - PAD_RIGHT}
          y2={budgetLineY}
          stroke="#9CA3AF"
          strokeWidth={1}
          strokeDasharray="4 3"
          opacity={0.7}
        />
        <text
          x={SVG_WIDTH - PAD_RIGHT}
          y={budgetLineY - 2}
          textAnchor="end"
          fill="#9CA3AF"
          className="text-[7px]"
        >
          max {maxEpsilon.toFixed(1)}
        </text>

        {/* Area fill */}
        <path d={areaPath} fill={`url(#${uid}-budget-fill)`} />

        {/* Line */}
        <path d={linePath} fill="none" stroke={stroke} strokeWidth={1.5} strokeLinejoin="round" />

        {/* Left Y labels: 0 and max */}
        <text x={PAD_LEFT - 4} y={PAD_TOP + DRAW_H + 3} textAnchor="end" fill="#9CA3AF" className="text-[8px]">
          0
        </text>
        <text x={PAD_LEFT - 4} y={PAD_TOP + 4} textAnchor="end" fill="#9CA3AF" className="text-[8px]">
          {maxEpsilon.toFixed(1)}
        </text>

        {/* X-axis labels: first and last round */}
        {rounds.length > 0 && (
          <>
            <text x={scaleX(0, count)} y={SVG_HEIGHT - 2} textAnchor="middle" fill="#9CA3AF" className="text-[8px]">
              R{rounds[0].round_number}
            </text>
            {rounds.length > 1 && (
              <text
                x={scaleX(count - 1, count)}
                y={SVG_HEIGHT - 2}
                textAnchor="middle"
                fill="#9CA3AF"
                className="text-[8px]"
              >
                R{rounds[rounds.length - 1].round_number}
              </text>
            )}
          </>
        )}
      </svg>

      {/* Footer info */}
      <div className="flex items-center justify-between mt-1 text-[10px]">
        <span className="text-gray-500">
          Used:{" "}
          <span className={ratio > 0.9 ? "text-red-600 font-semibold" : ratio > 0.7 ? "text-amber-600 font-semibold" : "text-blue-600"}>
            {currentTotal.toFixed(2)} / {maxEpsilon.toFixed(1)}
          </span>{" "}
          ({(ratio * 100).toFixed(0)}%)
        </span>
        <span className="text-gray-400">
          {roundsRemaining === Infinity
            ? "No spend yet"
            : roundsRemaining <= 0
              ? "Budget exhausted"
              : `Budget exhausted in ~${roundsRemaining} rounds`}
        </span>
      </div>
    </div>
  );
}
