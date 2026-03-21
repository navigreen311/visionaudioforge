"use client";

import React, { useMemo, useId } from "react";
import type { EpochData } from "./types";

interface TrainingChartsProps {
  epochs: EpochData[];
  bestEpoch?: number;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

interface Point {
  x: number;
  y: number;
}

function buildPoints(
  values: (number | null)[],
  xPositions: number[],
  yMin: number,
  yRange: number,
  chartHeight: number,
  padY: number,
): Point[] {
  const drawH = chartHeight - padY * 2;
  return values.reduce<Point[]>((acc, v, i) => {
    if (v !== null) {
      const y = padY + drawH - ((v - yMin) / (yRange || 1)) * drawH;
      acc.push({ x: xPositions[i], y });
    }
    return acc;
  }, []);
}

function pointsToPath(pts: Point[]): string {
  if (pts.length === 0) return "";
  return pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
}

/* ------------------------------------------------------------------ */
/*  Single chart                                                      */
/* ------------------------------------------------------------------ */

interface LineConfig {
  values: (number | null)[];
  color: string;
  label: string;
}

interface ChartPanelProps {
  title: string;
  lines: LineConfig[];
  epochNumbers: number[];
  bestEpoch?: number;
  /** Unique prefix for gradient IDs */
  idPrefix: string;
}

const CHART_HEIGHT = 200;
const PAD_LEFT = 48;
const PAD_RIGHT = 12;
const PAD_Y = 20;

function ChartPanel({ title, lines, epochNumbers, bestEpoch, idPrefix }: ChartPanelProps) {
  const computed = useMemo(() => {
    // Compute global Y range across all lines
    const allVals = lines.flatMap((l) => l.values.filter((v): v is number => v !== null));
    if (allVals.length === 0) return null;

    const yMin = Math.min(...allVals);
    const yMax = Math.max(...allVals);
    const yRange = yMax - yMin;

    return { yMin, yMax, yRange };
  }, [lines]);

  if (!computed || epochNumbers.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-sm text-gray-400">
        No data yet
      </div>
    );
  }

  const { yMin, yMax, yRange } = computed;

  // Y-axis ticks (5 ticks)
  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (yRange * i) / 4);

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{title}</h4>
      <svg
        viewBox={`0 0 600 ${CHART_HEIGHT}`}
        className="w-full"
        style={{ height: CHART_HEIGHT }}
        preserveAspectRatio="none"
        role="img"
        aria-label={`${title} chart`}
      >
        {/* Y-axis grid + labels */}
        {yTicks.map((tick) => {
          const drawH = CHART_HEIGHT - PAD_Y * 2;
          const y = PAD_Y + drawH - ((tick - yMin) / (yRange || 1)) * drawH;
          return (
            <g key={tick}>
              <line x1={PAD_LEFT} y1={y} x2={600 - PAD_RIGHT} y2={y} stroke="#E5E7EB" strokeWidth={0.5} />
              <text x={PAD_LEFT - 4} y={y + 3} textAnchor="end" className="text-[9px]" fill="#9CA3AF">
                {tick < 1 ? tick.toFixed(3) : tick.toFixed(1)}
              </text>
            </g>
          );
        })}

        {/* X positions */}
        {(() => {
          const drawW = 600 - PAD_LEFT - PAD_RIGHT;
          const step = epochNumbers.length > 1 ? drawW / (epochNumbers.length - 1) : 0;
          const xPositions = epochNumbers.map((_, i) => PAD_LEFT + i * step);

          // Best epoch vertical line
          const bestIdx = bestEpoch !== undefined ? epochNumbers.indexOf(bestEpoch) : -1;

          return (
            <>
              {/* Best epoch marker */}
              {bestIdx >= 0 && (
                <line
                  x1={xPositions[bestIdx]}
                  y1={PAD_Y}
                  x2={xPositions[bestIdx]}
                  y2={CHART_HEIGHT - PAD_Y}
                  stroke="#16A34A"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  opacity={0.7}
                />
              )}

              {/* Lines */}
              {lines.map((line) => {
                const pts = buildPoints(line.values, xPositions, yMin, yRange, CHART_HEIGHT, PAD_Y);
                const gradId = `${idPrefix}-${line.label.replace(/\s+/g, "")}`;
                if (pts.length === 0) return null;
                return (
                  <g key={line.label}>
                    <defs>
                      <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={line.color} stopOpacity={0.15} />
                        <stop offset="100%" stopColor={line.color} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    {/* Area fill */}
                    <path
                      d={`${pointsToPath(pts)} L ${pts[pts.length - 1].x.toFixed(1)},${CHART_HEIGHT - PAD_Y} L ${pts[0].x.toFixed(1)},${CHART_HEIGHT - PAD_Y} Z`}
                      fill={`url(#${gradId})`}
                    />
                    {/* Line */}
                    <path d={pointsToPath(pts)} fill="none" stroke={line.color} strokeWidth={1.5} strokeLinejoin="round" />
                    {/* Dots */}
                    {pts.map((p, i) => (
                      <circle key={i} cx={p.x} cy={p.y} r={2} fill={line.color} />
                    ))}
                  </g>
                );
              })}

              {/* X-axis labels (show up to 10 evenly spaced) */}
              {epochNumbers
                .filter((_, i) => {
                  if (epochNumbers.length <= 10) return true;
                  const every = Math.ceil(epochNumbers.length / 10);
                  return i % every === 0 || i === epochNumbers.length - 1;
                })
                .map((ep) => {
                  const idx = epochNumbers.indexOf(ep);
                  return (
                    <text
                      key={ep}
                      x={xPositions[idx]}
                      y={CHART_HEIGHT - 4}
                      textAnchor="middle"
                      className="text-[9px]"
                      fill="#9CA3AF"
                    >
                      {ep}
                    </text>
                  );
                })}
            </>
          );
        })()}
      </svg>

      {/* Legend */}
      <div className="flex gap-4 mt-1">
        {lines.map((l) => (
          <span key={l.label} className="inline-flex items-center gap-1.5 text-[10px] text-gray-500">
            <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: l.color }} />
            {l.label}
          </span>
        ))}
        {bestEpoch !== undefined && (
          <span className="inline-flex items-center gap-1.5 text-[10px] text-green-600">
            <span className="inline-block h-0.5 w-3 border-t-2 border-dashed border-green-500" />
            Best epoch
          </span>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Export                                                             */
/* ------------------------------------------------------------------ */

export default function TrainingCharts({ epochs, bestEpoch }: TrainingChartsProps) {
  const uid = useId();
  const epochNumbers = epochs.map((e) => e.epoch_number);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <ChartPanel
        title="Loss"
        idPrefix={`${uid}-loss`}
        epochNumbers={epochNumbers}
        bestEpoch={bestEpoch}
        lines={[
          { values: epochs.map((e) => e.train_loss), color: "#2563EB", label: "Train Loss" },
          { values: epochs.map((e) => e.val_loss), color: "#F59E0B", label: "Val Loss" },
        ]}
      />
      <ChartPanel
        title="Accuracy"
        idPrefix={`${uid}-acc`}
        epochNumbers={epochNumbers}
        bestEpoch={bestEpoch}
        lines={[
          { values: epochs.map((e) => e.train_acc), color: "#2563EB", label: "Train Acc" },
          { values: epochs.map((e) => e.val_acc), color: "#F59E0B", label: "Val Acc" },
        ]}
      />
    </div>
  );
}
