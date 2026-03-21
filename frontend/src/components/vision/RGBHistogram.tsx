"use client";

import React, { useState, useMemo, useCallback, useRef } from "react";

// ── Types ──────────────────────────────────────────────────────────

interface HistogramData {
  r: number[];
  g: number[];
  b: number[];
}

interface RGBHistogramProps {
  histogram?: HistogramData;
}

type Channel = "r" | "g" | "b" | "l";

interface ChannelConfig {
  key: Channel;
  label: string;
  color: string;
  opacity: number;
}

interface TooltipInfo {
  bin: number;
  r: number;
  g: number;
  b: number;
  l: number;
  x: number;
  y: number;
}

const CHANNELS: ChannelConfig[] = [
  { key: "r", label: "R", color: "#ef4444", opacity: 0.6 },
  { key: "g", label: "G", color: "#22c55e", opacity: 0.6 },
  { key: "b", label: "B", color: "#3b82f6", opacity: 0.6 },
  { key: "l", label: "L", color: "#6b7280", opacity: 0.4 },
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
const BIN_COUNT = 256;

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

export default function RGBHistogram({ histogram }: RGBHistogramProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [visible, setVisible] = useState<Record<Channel, boolean>>({
    r: true,
    g: true,
    b: true,
    l: true,
  });
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  const toggle = (ch: Channel) => {
    setVisible((prev) => ({ ...prev, [ch]: !prev[ch] }));
  };

  const computed = useMemo(() => {
    if (!histogram) return null;

    const luminance = computeLuminance(histogram.r, histogram.g, histogram.b);
    const allValues = [
      ...histogram.r,
      ...histogram.g,
      ...histogram.b,
      ...luminance,
    ];
    const maxVal = Math.max(...allValues, 1);

    return {
      luminance,
      lines: {
        r: buildPolyline(histogram.r, maxVal),
        g: buildPolyline(histogram.g, maxVal),
        b: buildPolyline(histogram.b, maxVal),
        l: buildPolyline(luminance, maxVal),
      },
      maxVal,
    };
  }, [histogram]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!histogram || !svgRef.current || !computed) return;

      const svg = svgRef.current;
      const rect = svg.getBoundingClientRect();
      const scaleX = SVG_W / rect.width;
      const svgX = (e.clientX - rect.left) * scaleX;

      const plotX = svgX - PAD_LEFT;
      if (plotX < 0 || plotX > PLOT_W) {
        setTooltip(null);
        return;
      }

      const bin = Math.round((plotX / PLOT_W) * (BIN_COUNT - 1));
      const clampedBin = Math.max(0, Math.min(BIN_COUNT - 1, bin));

      setTooltip({
        bin: clampedBin,
        r: Math.round(histogram.r[clampedBin] ?? 0),
        g: Math.round(histogram.g[clampedBin] ?? 0),
        b: Math.round(histogram.b[clampedBin] ?? 0),
        l: Math.round(computed.luminance[clampedBin] ?? 0),
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    },
    [histogram, computed],
  );

  const handleMouseLeave = useCallback(() => setTooltip(null), []);

  if (!histogram) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border border-gray-200 bg-gray-50">
        <p className="text-sm text-gray-400">
          Analyze an image to see histogram
        </p>
      </div>
    );
  }

  const yTicks = 5;

  return (
    <div className="relative rounded-lg border border-gray-200 bg-white p-4">
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
        ref={svgRef}
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        className="w-full"
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
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

        {/* Hover crosshair */}
        {tooltip && (
          <line
            x1={PAD_LEFT + (tooltip.bin / (BIN_COUNT - 1)) * PLOT_W}
            y1={PAD_TOP}
            x2={PAD_LEFT + (tooltip.bin / (BIN_COUNT - 1)) * PLOT_W}
            y2={PAD_TOP + PLOT_H}
            stroke="#9ca3af"
            strokeWidth={0.5}
            strokeDasharray="4 2"
            pointerEvents="none"
          />
        )}

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

      {/* Tooltip overlay */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-md border border-gray-200 bg-white/95 px-3 py-2 text-xs shadow-lg backdrop-blur-sm"
          style={{
            left: Math.min(
              tooltip.x + 12,
              (svgRef.current?.getBoundingClientRect().width ?? 300) - 140,
            ),
            top: tooltip.y - 10,
          }}
        >
          <p className="mb-1 font-semibold text-gray-700">
            Bin {tooltip.bin}
          </p>
          {visible.r && (
            <p style={{ color: "#ef4444" }}>
              R: {tooltip.r.toLocaleString()}
            </p>
          )}
          {visible.g && (
            <p style={{ color: "#16a34a" }}>
              G: {tooltip.g.toLocaleString()}
            </p>
          )}
          {visible.b && (
            <p style={{ color: "#3b82f6" }}>
              B: {tooltip.b.toLocaleString()}
            </p>
          )}
          {visible.l && (
            <p style={{ color: "#6b7280" }}>
              L: {tooltip.l.toLocaleString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
