"use client";

import React from "react";

interface CircularGaugeProps {
  /** Percentage value between 0 and 100, or null when the host does not
   *  report it. Null renders as an em dash rather than a plausible zero. */
  value: number | null | undefined;
  /** Label displayed below the gauge. */
  label: string;
  /** Optional secondary label (e.g. "2.4 / 50 GB") shown below the percentage. */
  maxLabel?: string;
}

/** Return a colour that reflects severity: green, amber, or red. */
function getGaugeColor(pct: number): string {
  if (pct >= 80) return "#EF4444"; // red
  if (pct >= 60) return "#F59E0B"; // amber
  return "#10B981"; // green
}

const SIZE = 100;
const STROKE_WIDTH = 8;
const RADIUS = (SIZE - STROKE_WIDTH) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function CircularGauge({
  value,
  label,
  maxLabel,
}: CircularGaugeProps) {
  const known = typeof value === "number" && Number.isFinite(value);
  const clamped = known ? Math.min(Math.max(value as number, 0), 100) : 0;
  const color = getGaugeColor(clamped);
  const dashOffset = CIRCUMFERENCE - (clamped / 100) * CIRCUMFERENCE;
  const center = SIZE / 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: SIZE, height: SIZE }}>
        <svg
          width={SIZE}
          height={SIZE}
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="transform -rotate-90"
          aria-label={`${label}: ${known ? `${Math.round(clamped)}%` : "not measured"}`}
          role="img"
        >
          {/* Background track */}
          <circle
            cx={center}
            cy={center}
            r={RADIUS}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={STROKE_WIDTH}
          />
          {/* Progress arc */}
          <circle
            cx={center}
            cy={center}
            r={RADIUS}
            fill="none"
            stroke={color}
            strokeWidth={STROKE_WIDTH}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            style={{
              transition: "stroke-dashoffset 0.7s cubic-bezier(.4,0,.2,1), stroke 0.5s ease",
            }}
          />
        </svg>
        {/* Center text overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-semibold text-gray-900">
            {known ? `${Math.round(clamped)}%` : "—"}
          </span>
          {maxLabel && (
            <span className="text-[10px] leading-tight text-gray-500">
              {maxLabel}
            </span>
          )}
        </div>
      </div>
      <span className="text-xs font-medium text-gray-600 text-center">
        {label}
      </span>
    </div>
  );
}
