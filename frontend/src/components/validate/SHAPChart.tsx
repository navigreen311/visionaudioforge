"use client";

import React from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SHAPValue {
  feature: string;
  value: number;
}

interface Prediction {
  className: string;
  confidence: number;
}

interface SHAPChartProps {
  shapValues: SHAPValue[];
  predictions?: Prediction[];
}

/* ------------------------------------------------------------------ */
/*  SHAP Bar Chart (horizontal)                                        */
/* ------------------------------------------------------------------ */

function SHAPBarChart({ shapValues }: { shapValues: SHAPValue[] }) {
  const sorted = [...shapValues].sort(
    (a, b) => Math.abs(b.value) - Math.abs(a.value),
  );
  const maxAbs = Math.max(...sorted.map((s) => Math.abs(s.value)), 0.01);

  const BAR_HEIGHT = 28;
  const LABEL_WIDTH = 140;
  const VALUE_WIDTH = 60;
  const CHART_WIDTH = 320;
  const SVG_WIDTH = LABEL_WIDTH + CHART_WIDTH + VALUE_WIDTH + 16;
  const SVG_HEIGHT = sorted.length * BAR_HEIGHT + 8;
  const CENTER_X = LABEL_WIDTH + CHART_WIDTH / 2;

  return (
    <svg
      viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
      className="w-full"
      role="img"
      aria-label="SHAP feature importance chart"
    >
      {/* Center axis */}
      <line
        x1={CENTER_X}
        y1={0}
        x2={CENTER_X}
        y2={SVG_HEIGHT}
        stroke="#d1d5db"
        strokeWidth={1}
      />

      {sorted.map((item, i) => {
        const y = i * BAR_HEIGHT + 4;
        const barWidth = (Math.abs(item.value) / maxAbs) * (CHART_WIDTH / 2);
        const isPositive = item.value >= 0;
        const barX = isPositive ? CENTER_X : CENTER_X - barWidth;
        const barColor = isPositive ? "#3b82f6" : "#ef4444"; // blue / red

        return (
          <g key={item.feature}>
            {/* Feature label */}
            <text
              x={LABEL_WIDTH - 8}
              y={y + BAR_HEIGHT / 2}
              textAnchor="end"
              dominantBaseline="central"
              className="fill-gray-700"
              fontSize={12}
            >
              {item.feature.length > 18
                ? `${item.feature.slice(0, 16)}...`
                : item.feature}
            </text>

            {/* Bar */}
            <rect
              x={barX}
              y={y + 4}
              width={barWidth}
              height={BAR_HEIGHT - 10}
              rx={3}
              fill={barColor}
              opacity={0.85}
            />

            {/* Value label */}
            <text
              x={LABEL_WIDTH + CHART_WIDTH + 8}
              y={y + BAR_HEIGHT / 2}
              textAnchor="start"
              dominantBaseline="central"
              className="fill-gray-600"
              fontSize={11}
            >
              {item.value >= 0 ? "+" : ""}
              {item.value.toFixed(3)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Predictions Bar Chart (top-5)                                      */
/* ------------------------------------------------------------------ */

function PredictionsChart({ predictions }: { predictions: Prediction[] }) {
  const top5 = [...predictions]
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 5);

  return (
    <div className="space-y-2">
      {top5.map((pred) => (
        <div key={pred.className} className="flex items-center gap-3">
          <span className="w-32 truncate text-sm font-medium text-gray-700">
            {pred.className}
          </span>
          <div className="flex-1 h-5 bg-gray-100 rounded overflow-hidden">
            <div
              className="h-full rounded bg-brand-500 transition-all"
              style={{ width: `${(pred.confidence * 100).toFixed(1)}%` }}
            />
          </div>
          <span className="w-14 text-right text-sm text-gray-600">
            {(pred.confidence * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Combined Export                                                     */
/* ------------------------------------------------------------------ */

export default function SHAPChart({ shapValues, predictions }: SHAPChartProps) {
  return (
    <div className="space-y-6">
      {predictions && predictions.length > 0 && (
        <div>
          <h4 className="mb-3 text-sm font-semibold text-gray-800">
            Top-5 Predictions
          </h4>
          <PredictionsChart predictions={predictions} />
        </div>
      )}

      {shapValues.length > 0 && (
        <div>
          <h4 className="mb-3 text-sm font-semibold text-gray-800">
            SHAP Feature Attributions
          </h4>
          <div className="flex items-center gap-4 mb-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="inline-block h-3 w-3 rounded bg-blue-500" />
              Pushes toward prediction
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-3 w-3 rounded bg-red-500" />
              Pushes away from prediction
            </span>
          </div>
          <SHAPBarChart shapValues={shapValues} />
        </div>
      )}

      {shapValues.length === 0 && (!predictions || predictions.length === 0) && (
        <p className="text-sm text-gray-400 text-center py-8">
          No explanation data available yet.
        </p>
      )}
    </div>
  );
}
