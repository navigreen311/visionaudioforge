"use client";

import React, { useState, useMemo, useCallback } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CellDetail {
  row: string;
  col: string;
  value: number;
}

interface ConfusionMatrixHeatmapProps {
  labels: string[];
  values: number[][];
  /** Callback when a cell is clicked */
  onCellClick?: (detail: CellDetail) => void;
}

/* ------------------------------------------------------------------ */
/*  Layout constants                                                   */
/* ------------------------------------------------------------------ */

const MATRIX_SIZE = 200;
const LABEL_OFFSET = 50;
const SVG_SIZE = MATRIX_SIZE + LABEL_OFFSET + 10;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function interpolateColor(ratio: number): string {
  // Light blue (#dbeafe) -> Dark blue (#1e3a8a)
  const r = Math.round(219 - ratio * (219 - 30));
  const g = Math.round(234 - ratio * (234 - 58));
  const b = Math.round(254 - ratio * (254 - 138));
  return `rgb(${r},${g},${b})`;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function ConfusionMatrixHeatmap({
  labels,
  values,
  onCellClick,
}: ConfusionMatrixHeatmapProps) {
  const [hoveredCell, setHoveredCell] = useState<CellDetail | null>(null);

  const maxValue = useMemo(() => {
    let max = 0;
    for (const row of values) {
      for (const v of row) {
        if (v > max) max = v;
      }
    }
    return max || 1;
  }, [values]);

  const cellSize = useMemo(
    () => MATRIX_SIZE / labels.length,
    [labels.length],
  );

  const handleCellClick = useCallback(
    (row: string, col: string, value: number) => {
      onCellClick?.({ row, col, value });
    },
    [onCellClick],
  );

  return (
    <div className="relative inline-block">
      <svg
        width={SVG_SIZE}
        height={SVG_SIZE}
        viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
        className="select-none"
      >
        {/* Y-axis labels */}
        {labels.map((label, i) => (
          <text
            key={`y-${label}`}
            x={LABEL_OFFSET - 6}
            y={LABEL_OFFSET + i * cellSize + cellSize / 2}
            textAnchor="end"
            dominantBaseline="central"
            className="fill-gray-600"
            fontSize={Math.min(11, cellSize * 0.6)}
          >
            {label.length > 6 ? `${label.slice(0, 5)}…` : label}
          </text>
        ))}

        {/* X-axis labels */}
        {labels.map((label, j) => (
          <text
            key={`x-${label}`}
            x={LABEL_OFFSET + j * cellSize + cellSize / 2}
            y={LABEL_OFFSET - 6}
            textAnchor="middle"
            dominantBaseline="auto"
            className="fill-gray-600"
            fontSize={Math.min(11, cellSize * 0.6)}
          >
            {label.length > 6 ? `${label.slice(0, 5)}…` : label}
          </text>
        ))}

        {/* Axis titles */}
        <text
          x={LABEL_OFFSET + MATRIX_SIZE / 2}
          y={12}
          textAnchor="middle"
          className="fill-gray-500"
          fontSize={10}
          fontWeight={600}
        >
          Predicted
        </text>
        <text
          x={12}
          y={LABEL_OFFSET + MATRIX_SIZE / 2}
          textAnchor="middle"
          className="fill-gray-500"
          fontSize={10}
          fontWeight={600}
          transform={`rotate(-90, 12, ${LABEL_OFFSET + MATRIX_SIZE / 2})`}
        >
          Actual
        </text>

        {/* Heatmap cells */}
        {values.map((row, i) =>
          row.map((value, j) => {
            const ratio = value / maxValue;
            const isHovered =
              hoveredCell?.row === labels[i] && hoveredCell?.col === labels[j];

            return (
              <g key={`cell-${i}-${j}`}>
                <rect
                  x={LABEL_OFFSET + j * cellSize}
                  y={LABEL_OFFSET + i * cellSize}
                  width={cellSize - 1}
                  height={cellSize - 1}
                  fill={interpolateColor(ratio)}
                  stroke={isHovered ? "#1e40af" : "white"}
                  strokeWidth={isHovered ? 2 : 0.5}
                  rx={2}
                  className="cursor-pointer transition-opacity"
                  onClick={() => handleCellClick(labels[i], labels[j], value)}
                  onMouseEnter={() =>
                    setHoveredCell({ row: labels[i], col: labels[j], value })
                  }
                  onMouseLeave={() => setHoveredCell(null)}
                />
                <text
                  x={LABEL_OFFSET + j * cellSize + (cellSize - 1) / 2}
                  y={LABEL_OFFSET + i * cellSize + (cellSize - 1) / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={Math.min(12, cellSize * 0.45)}
                  fontWeight={600}
                  fill={ratio > 0.55 ? "white" : "#1e293b"}
                  className="pointer-events-none"
                >
                  {value}
                </text>
              </g>
            );
          }),
        )}
      </svg>

      {/* Tooltip */}
      {hoveredCell && (
        <div className="absolute z-10 rounded-md bg-gray-900 px-3 py-2 text-xs text-white shadow-lg -translate-x-1/2 pointer-events-none"
          style={{
            left: SVG_SIZE / 2,
            top: SVG_SIZE + 4,
          }}
        >
          <span className="font-semibold">Actual:</span> {hoveredCell.row}
          {" | "}
          <span className="font-semibold">Predicted:</span> {hoveredCell.col}
          {" | "}
          <span className="font-semibold">Count:</span> {hoveredCell.value}
        </div>
      )}
    </div>
  );
}
