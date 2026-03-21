"use client";

import React from "react";

interface CircularGaugeProps {
  value: number;
  max: number;
  label: string;
  unit: string;
  size?: number;
  strokeWidth?: number;
  showPercentage?: boolean;
}

function getGaugeColor(pct: number): string {
  if (pct >= 80) return "#A32D2D";
  if (pct >= 60) return "#D97706";
  return "#0F6E56";
}

export default function CircularGauge({
  value,
  max,
  label,
  unit,
  size = 120,
  strokeWidth = 10,
  showPercentage = true,
}: CircularGaugeProps) {
  const clampedValue = Math.min(Math.max(value, 0), max);
  const percentage = max > 0 ? (clampedValue / max) * 100 : 0;
  const color = getGaugeColor(percentage);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (percentage / 100) * circumference;
  const center = size / 2;

  const displayValue = showPercentage
    ? `${Math.round(percentage)}%`
    : `${clampedValue}`;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="transform -rotate-90"
        aria-label={`${label}: ${Math.round(percentage)}%`}
        role="img"
      >
        {/* Background track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-in-out"
        />
      </svg>
      {/* Center text overlay */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center"
      >
        <span
          className="font-semibold text-gray-900"
          style={{ fontSize: size * 0.18 }}
        >
          {displayValue}
        </span>
        {!showPercentage && (
          <span
            className="text-gray-500"
            style={{ fontSize: size * 0.12 }}
          >
            {unit}
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
