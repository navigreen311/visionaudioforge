"use client";

import React, { useMemo, useState, useId } from "react";
import type { RoundData, ParticipantInfo } from "./types";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface ContributionChartProps {
  rounds: RoundData[];
  participants: ParticipantInfo[];
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const CHART_HEIGHT = 160;
const PAD_LEFT = 36;
const PAD_RIGHT = 12;
const PAD_TOP = 8;
const PAD_BOTTOM = 20;

const SITE_COLORS: Record<string, string> = {
  "site-alpha": "#2563EB", // blue
  "site-beta": "#0D9488",  // teal
  "site-gamma": "#D97706", // amber
  "site-delta": "#F97066", // coral
};

const DEFAULT_PALETTE = ["#6366F1", "#EC4899", "#14B8A6", "#F59E0B", "#8B5CF6", "#EF4444"];

function getColor(siteId: string, index: number): string {
  return SITE_COLORS[siteId] ?? DEFAULT_PALETTE[index % DEFAULT_PALETTE.length];
}

/* ------------------------------------------------------------------ */
/*  Data computation                                                   */
/* ------------------------------------------------------------------ */

interface StackedPoint {
  round: number;
  /** Cumulative percentages per participant (bottom to top), keyed by participant id */
  layers: Map<string, { y0: number; y1: number }>;
}

function buildStackedData(
  rounds: RoundData[],
  participantIds: string[],
): StackedPoint[] {
  return rounds.map((r) => {
    // Count total samples in this round
    const totalSamples = r.siteUpdates.reduce((sum, su) => sum + su.samplesUsed, 0);
    const siteMap = new Map(r.siteUpdates.map((su) => [su.siteId, su.samplesUsed]));

    let cumulative = 0;
    const layers = new Map<string, { y0: number; y1: number }>();

    for (const pid of participantIds) {
      const samples = siteMap.get(pid) ?? 0;
      const pct = totalSamples > 0 ? (samples / totalSamples) * 100 : 0;
      const y0 = cumulative;
      cumulative += pct;
      layers.set(pid, { y0, y1: cumulative });
    }

    return { round: r.round, layers };
  });
}

/* ------------------------------------------------------------------ */
/*  SVG helpers                                                        */
/* ------------------------------------------------------------------ */

function buildAreaPath(
  points: StackedPoint[],
  participantId: string,
  xPositions: number[],
  drawH: number,
): string {
  if (points.length === 0) return "";

  // Top line (y1) left-to-right
  const topParts: string[] = [];
  // Bottom line (y0) right-to-left
  const bottomParts: string[] = [];

  for (let i = 0; i < points.length; i++) {
    const layer = points[i].layers.get(participantId);
    const y1 = layer ? PAD_TOP + drawH - (layer.y1 / 100) * drawH : PAD_TOP + drawH;
    const y0 = layer ? PAD_TOP + drawH - (layer.y0 / 100) * drawH : PAD_TOP + drawH;
    const x = xPositions[i];

    topParts.push(`${i === 0 ? "M" : "L"} ${x.toFixed(1)},${y1.toFixed(1)}`);
    bottomParts.unshift(`L ${x.toFixed(1)},${y0.toFixed(1)}`);
  }

  return `${topParts.join(" ")} ${bottomParts.join(" ")} Z`;
}

/* ------------------------------------------------------------------ */
/*  Tooltip                                                            */
/* ------------------------------------------------------------------ */

interface TooltipData {
  round: number;
  x: number;
  y: number;
  breakdown: { siteId: string; label: string; pct: number; color: string }[];
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ContributionChart({ rounds, participants }: ContributionChartProps) {
  const uid = useId();
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  const participantIds = useMemo(() => participants.map((p) => p.id), [participants]);

  const stacked = useMemo(
    () => buildStackedData(rounds, participantIds),
    [rounds, participantIds],
  );

  const svgWidth = 600;
  const drawW = svgWidth - PAD_LEFT - PAD_RIGHT;
  const drawH = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM;

  const xPositions = useMemo(() => {
    if (rounds.length <= 1) return rounds.map(() => PAD_LEFT);
    const step = drawW / (rounds.length - 1);
    return rounds.map((_, i) => PAD_LEFT + i * step);
  }, [rounds.length, drawW]);

  // Y-axis ticks
  const yTicks = [0, 25, 50, 75, 100];

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * svgWidth;

    // Find nearest round
    let nearest = 0;
    let minDist = Infinity;
    for (let i = 0; i < xPositions.length; i++) {
      const dist = Math.abs(mouseX - xPositions[i]);
      if (dist < minDist) {
        minDist = dist;
        nearest = i;
      }
    }

    if (nearest >= stacked.length) return;

    const point = stacked[nearest];
    const breakdown = participantIds.map((pid, idx) => {
      const layer = point.layers.get(pid);
      const pLabel = participants.find((p) => p.id === pid)?.label ?? pid;
      return {
        siteId: pid,
        label: pLabel,
        pct: layer ? layer.y1 - layer.y0 : 0,
        color: getColor(pid, idx),
      };
    }).filter((b) => b.pct > 0);

    setTooltip({
      round: point.round,
      x: xPositions[nearest],
      y: PAD_TOP + 10,
      breakdown,
    });
  };

  if (rounds.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-gray-400" style={{ height: CHART_HEIGHT }}>
        No contribution data yet
      </div>
    );
  }

  return (
    <div>
      <div className="relative">
        <svg
          viewBox={`0 0 ${svgWidth} ${CHART_HEIGHT}`}
          className="w-full"
          style={{ height: CHART_HEIGHT }}
          preserveAspectRatio="none"
          role="img"
          aria-label="Participant contribution stacked area chart"
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setTooltip(null)}
        >
          {/* Y-axis grid + labels */}
          {yTicks.map((tick) => {
            const y = PAD_TOP + drawH - (tick / 100) * drawH;
            return (
              <g key={tick}>
                <line
                  x1={PAD_LEFT}
                  y1={y}
                  x2={svgWidth - PAD_RIGHT}
                  y2={y}
                  stroke="#E5E7EB"
                  strokeWidth={0.5}
                />
                <text
                  x={PAD_LEFT - 4}
                  y={y + 3}
                  textAnchor="end"
                  className="text-[9px]"
                  fill="#9CA3AF"
                >
                  {tick}%
                </text>
              </g>
            );
          })}

          {/* Stacked areas (render bottom-to-top, so first participant is at the bottom) */}
          {participantIds.map((pid, idx) => {
            const color = getColor(pid, idx);
            const gradId = `${uid}-area-${pid}`;
            const path = buildAreaPath(stacked, pid, xPositions, drawH);
            if (!path) return null;

            return (
              <g key={pid}>
                <defs>
                  <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity={0.85} />
                    <stop offset="100%" stopColor={color} stopOpacity={0.55} />
                  </linearGradient>
                </defs>
                <path d={path} fill={`url(#${gradId})`} stroke={color} strokeWidth={0.5} />
              </g>
            );
          })}

          {/* X-axis labels */}
          {rounds
            .filter((_, i) => {
              if (rounds.length <= 15) return true;
              const every = Math.ceil(rounds.length / 12);
              return i % every === 0 || i === rounds.length - 1;
            })
            .map((r) => {
              const idx = rounds.indexOf(r);
              return (
                <text
                  key={r.round}
                  x={xPositions[idx]}
                  y={CHART_HEIGHT - 4}
                  textAnchor="middle"
                  className="text-[9px]"
                  fill="#9CA3AF"
                >
                  {r.round}
                </text>
              );
            })}

          {/* Hover vertical line */}
          {tooltip && (
            <line
              x1={tooltip.x}
              y1={PAD_TOP}
              x2={tooltip.x}
              y2={PAD_TOP + drawH}
              stroke="#6B7280"
              strokeWidth={1}
              strokeDasharray="3 2"
              opacity={0.6}
            />
          )}
        </svg>

        {/* HTML tooltip overlay */}
        {tooltip && (
          <div
            className="absolute pointer-events-none bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs z-10"
            style={{
              left: `${(tooltip.x / svgWidth) * 100}%`,
              top: 4,
              transform: "translateX(-50%)",
              minWidth: 140,
            }}
          >
            <p className="font-semibold text-gray-700 mb-1">Round {tooltip.round}</p>
            {tooltip.breakdown.map((b) => (
              <div key={b.siteId} className="flex items-center justify-between gap-3 py-0.5">
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ backgroundColor: b.color }}
                  />
                  {b.label}
                </span>
                <span className="tabular-nums font-medium">{b.pct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-2">
        {participants.map((p, idx) => (
          <span
            key={p.id}
            className="inline-flex items-center gap-1.5 text-[11px] text-gray-600"
          >
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: getColor(p.id, idx) }}
            />
            {p.label}
          </span>
        ))}
      </div>
    </div>
  );
}
