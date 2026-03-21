"use client";

import React, { useMemo, useCallback, useId } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface PRPoint {
  recall: number;
  precision: number;
  threshold: number;
}

interface PRCurveChartProps {
  data: PRPoint[];
  currentThreshold: number;
  onThresholdChange: (threshold: number) => void;
  aucPR: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const W = 320;
const H = 260;
const PAD = { top: 24, right: 20, bottom: 36, left: 44 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function toX(recall: number): number {
  return PAD.left + recall * PLOT_W;
}

function toY(precision: number): number {
  return PAD.top + (1 - precision) * PLOT_H;
}

function buildPath(points: PRPoint[]): string {
  if (points.length === 0) return "";
  return points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${toX(p.recall).toFixed(1)},${toY(p.precision).toFixed(1)}`)
    .join(" ");
}

function buildAreaPath(points: PRPoint[]): string {
  if (points.length === 0) return "";
  const line = buildPath(points);
  const lastX = toX(points[points.length - 1].recall).toFixed(1);
  const firstX = toX(points[0].recall).toFixed(1);
  const bottomY = toY(0).toFixed(1);
  return `${line} L ${lastX},${bottomY} L ${firstX},${bottomY} Z`;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function PRCurveChart({
  data,
  currentThreshold,
  onThresholdChange,
  aucPR,
}: PRCurveChartProps) {
  const uid = useId();
  const gradientId = `pr-fill-${uid}`;

  const markerPoint = useMemo(() => {
    if (data.length === 0) return null;
    let closest = data[0];
    let minDist = Math.abs(data[0].threshold - currentThreshold);
    for (const pt of data) {
      const d = Math.abs(pt.threshold - currentThreshold);
      if (d < minDist) {
        minDist = d;
        closest = pt;
      }
    }
    return closest;
  }, [data, currentThreshold]);

  const handleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const svg = e.currentTarget;
      const rect = svg.getBoundingClientRect();
      const svgX = ((e.clientX - rect.left) / rect.width) * W;
      const svgY = ((e.clientY - rect.top) / rect.height) * H;

      if (svgX < PAD.left || svgX > W - PAD.right || svgY < PAD.top || svgY > H - PAD.bottom) return;

      const clickRecall = (svgX - PAD.left) / PLOT_W;
      const clickPrecision = 1 - (svgY - PAD.top) / PLOT_H;

      let closest = data[0];
      let minDist = Infinity;
      for (const pt of data) {
        const d = Math.sqrt(
          Math.pow(pt.recall - clickRecall, 2) + Math.pow(pt.precision - clickPrecision, 2),
        );
        if (d < minDist) {
          minDist = d;
          closest = pt;
        }
      }
      if (closest) {
        onThresholdChange(closest.threshold);
      }
    },
    [data, onThresholdChange],
  );

  const ticks = [0, 0.2, 0.4, 0.6, 0.8, 1.0];

  const noSkillY = useMemo(() => {
    if (data.length === 0) return 0.5;
    return data[data.length - 1].precision;
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[260px] text-sm text-gray-400">
        No PR data
      </div>
    );
  }

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full cursor-crosshair"
        style={{ maxWidth: W, height: H }}
        role="img"
        aria-label="Precision-Recall curve"
        onClick={handleClick}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.15} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.03} />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} y1={toY(t)} x2={W - PAD.right} y2={toY(t)} stroke="#E5E7EB" strokeWidth={0.5} />
            <line x1={toX(t)} y1={PAD.top} x2={toX(t)} y2={H - PAD.bottom} stroke="#E5E7EB" strokeWidth={0.5} />
            <text x={PAD.left - 6} y={toY(t) + 3} textAnchor="end" fontSize={9} fill="#9CA3AF">
              {t.toFixed(1)}
            </text>
            <text x={toX(t)} y={H - PAD.bottom + 14} textAnchor="middle" fontSize={9} fill="#9CA3AF">
              {t.toFixed(1)}
            </text>
          </g>
        ))}

        {/* Axis titles */}
        <text x={PAD.left + PLOT_W / 2} y={H - 4} textAnchor="middle" fontSize={10} fill="#6B7280" fontWeight={500}>
          Recall
        </text>
        <text
          x={12}
          y={PAD.top + PLOT_H / 2}
          textAnchor="middle"
          fontSize={10}
          fill="#6B7280"
          fontWeight={500}
          transform={`rotate(-90, 12, ${PAD.top + PLOT_H / 2})`}
        >
          Precision
        </text>

        {/* No-skill baseline (dashed horizontal) */}
        <line
          x1={PAD.left} y1={toY(noSkillY)} x2={W - PAD.right} y2={toY(noSkillY)}
          stroke="#9CA3AF" strokeWidth={1} strokeDasharray="4 3" opacity={0.6}
        />

        {/* Filled area */}
        <path d={buildAreaPath(data)} fill={`url(#${gradientId})`} />

        {/* PR curve */}
        <path d={buildPath(data)} fill="none" stroke="#3b82f6" strokeWidth={2} strokeLinejoin="round" />

        {/* Threshold marker */}
        {markerPoint && (
          <>
            <line
              x1={toX(markerPoint.recall)} y1={PAD.top} x2={toX(markerPoint.recall)} y2={H - PAD.bottom}
              stroke="#ef4444" strokeWidth={1} strokeDasharray="3 2" opacity={0.5}
            />
            <line
              x1={PAD.left} y1={toY(markerPoint.precision)} x2={W - PAD.right} y2={toY(markerPoint.precision)}
              stroke="#ef4444" strokeWidth={1} strokeDasharray="3 2" opacity={0.5}
            />
            <circle
              cx={toX(markerPoint.recall)} cy={toY(markerPoint.precision)}
              r={5} fill="#ef4444" stroke="#fff" strokeWidth={2}
            />
          </>
        )}

        {/* AUC-PR badge */}
        <rect x={W - PAD.right - 76} y={PAD.top + 4} width={72} height={22} rx={4} fill="#EFF6FF" stroke="#BFDBFE" strokeWidth={0.5} />
        <text x={W - PAD.right - 40} y={PAD.top + 19} textAnchor="middle" fontSize={10} fill="#2563EB" fontWeight={600}>
          AUC {aucPR.toFixed(3)}
        </text>
      </svg>
    </div>
  );
}
