"use client";

import React, { useState, useMemo } from "react";

// ── Types ──────────────────────────────────────────────────────────

interface HistogramData {
  r: number[];
  g: number[];
  b: number[];
}

interface RGBHistogramProps {
  data: HistogramData | null;
}

type Channel = "r" | "g" | "b" | "l";

interface ChannelConfig {
  key: Channel;
  label: string;
  color: string;
  opacity: number;
}

const CHANNELS: ChannelConfig[] = [
  { key: "r", label: "R", color: "#ef4444", opacity: 0.6 },
  { key: "g", label: "G", color: "#22c55e", opacity: 0.6 },
  { key: "b", label: "B", color: "#3b82f6", opacity: 0.6 },
  { key: "l", label: "L", color: "#6b7280", opacity: 0.6 },
];

// ── Helpers ────────────────────────────────────────────────────────

const SVG_W = 512;
const SVG_H = 200;
const PAD_LEFT = 40;
const PAD_BOTTOM = 24;
const PAD_TOP = 8;
const PAD_RIGHT = 8;
const PLOT_W = SVG_W - PAD_LEFT - PAD_RIGHT;
const PLOT_H = SVG_H - PAD_TOP - PAD_BOTTOM;

function computeLuminance(r: number[], g: number[], b: number[]): number[] {
  const len = Math.min(r.length, g.length, b.length);
  const lum: number[] = new Array(len);
  for (let i = 0; i < len; i++) {
    lum[i] = 0.299 * r[i] + 0.587 * g[i] + 0.114 * b[i];
  }
  return lum;
}

function buildPolyline(values: number[], maxVal: number): string {
  if (values.length === 0 || maxVal === 0) return "";
  const points: string[] = [];
  const xScale = PLOT_W / (values.length - 1);
  for (let i = 0; i < values.length; i++) {
    const x = PAD_LEFT + i * xScale;
    const y = PAD_TOP + PLOT_H - (values[i] / maxVal) * PLOT_H;
    points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  return points.join(" ");
}

// ── Component ──────────────────────────────────────────────────────

export default function RGBHistogram({ data }: RGBHistogramProps) {
  const [visible, setVisible] = useState<Record<Channel, boolean>>({
    r: true,
    g: true,
    b: true,
    l: true,
  });

  const toggle = (ch: Channel) => {
    setVisible((prev) => ({ ...prev, [ch]: !prev[ch] }));
  };

  const computed = useMemo(() => {
    if (!data) return null;

    const luminance = computeLuminance(data.r, data.g, data.b);
    const allValues = [...data.r, ...data.g, ...data.b, ...luminance];
    const maxVal = Math.max(...allValues, 1);

    return {
      lines: {
        r: buildPolyline(data.r, maxVal),
        g: buildPolyline(data.g, maxVal),
        b: buildPolyline(data.b, maxVal),
        l: buildPolyline(luminance, maxVal),
      },
      maxVal,
    };
  }, [data]);

  if (!data) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border border-gray-200 bg-gray-50">
        <p className="text-sm text-gray-400">Analyze an image to see histogram</p>
      </div>
    );
  }

  const yTicks = 5;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      {/* Toggle buttons */}
      <div className="mb-3 flex gap-2">
        {CHANNELS.map((ch) => (
          <button
            key={ch.key}
            type="button"
            onClick={() => toggle(ch.key)}
            className={`rounded px-2.5 py-1 text-xs font-medium transition-opacity ${
              visible[ch.key] ? "opacity-100" : "opacity-40"
            }`}
            style={{
              backgroundColor: ch.color,
              color: "#fff",
            }}
          >
            {ch.label}
          </button>
        ))}
      </div>

      {/* SVG chart */}
      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        className="w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Y axis grid lines and labels */}
        {computed &&
          Array.from({ length: yTicks + 1 }).map((_, i) => {
            const frac = i / yTicks;
            const y = PAD_TOP + PLOT_H - frac * PLOT_H;
            const label = Math.round(frac * computed.maxVal);
            return (
              <g key={i}>
                <line
                  x1={PAD_LEFT}
                  y1={y}
                  x2={PAD_LEFT + PLOT_W}
                  y2={y}
                  stroke="#e5e7eb"
                  strokeWidth={0.5}
                />
                <text
                  x={PAD_LEFT - 4}
                  y={y + 3}
                  textAnchor="end"
                  className="fill-gray-400"
                  fontSize={8}
                >
                  {label}
                </text>
              </g>
            );
          })}

        {/* X axis labels */}
        {[0, 64, 128, 192, 255].map((v) => {
          const x = PAD_LEFT + (v / 255) * PLOT_W;
          return (
            <text
              key={v}
              x={x}
              y={SVG_H - 4}
              textAnchor="middle"
              className="fill-gray-400"
              fontSize={8}
            >
              {v}
            </text>
          );
        })}

        {/* Axes */}
        <line
          x1={PAD_LEFT}
          y1={PAD_TOP}
          x2={PAD_LEFT}
          y2={PAD_TOP + PLOT_H}
          stroke="#9ca3af"
          strokeWidth={1}
        />
        <line
          x1={PAD_LEFT}
          y1={PAD_TOP + PLOT_H}
          x2={PAD_LEFT + PLOT_W}
          y2={PAD_TOP + PLOT_H}
          stroke="#9ca3af"
          strokeWidth={1}
        />

        {/* Polylines */}
        {computed &&
          CHANNELS.map(
            (ch) =>
              visible[ch.key] &&
              computed.lines[ch.key] && (
                <polyline
                  key={ch.key}
                  points={computed.lines[ch.key]}
                  fill="none"
                  stroke={ch.color}
                  strokeWidth={1.2}
                  opacity={ch.opacity}
                />
              ),
          )}
      </svg>
    </div>
  );
}
