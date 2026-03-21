"use client";

import React, { useMemo, useState, useCallback } from "react";
import type { EpochData } from "./types";

interface EpochTableProps {
  epochs: EpochData[];
  bestEpoch?: number;
}

type SortKey = keyof EpochData;
type SortDir = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string; format: (v: number | null) => string }[] = [
  { key: "epoch_number", label: "Epoch", format: (v) => (v !== null ? String(v) : "-") },
  { key: "train_loss", label: "Train Loss", format: (v) => (v !== null ? v.toFixed(4) : "-") },
  { key: "val_loss", label: "Val Loss", format: (v) => (v !== null ? v.toFixed(4) : "-") },
  { key: "train_acc", label: "Train Acc", format: (v) => (v !== null ? `${(v * 100).toFixed(1)}%` : "-") },
  { key: "val_acc", label: "Val Acc", format: (v) => (v !== null ? `${(v * 100).toFixed(1)}%` : "-") },
  { key: "lr", label: "LR", format: (v) => (v !== null ? v.toExponential(2) : "-") },
  { key: "duration_s", label: "Duration", format: (v) => (v !== null ? `${v.toFixed(1)}s` : "-") },
];

export default function EpochTable({ epochs, bestEpoch }: EpochTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("epoch_number");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir("asc");
      }
    },
    [sortKey],
  );

  const sorted = useMemo(() => {
    const copy = [...epochs];
    copy.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return 1;
      if (bVal === null) return -1;
      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [epochs, sortKey, sortDir]);

  if (epochs.length === 0) {
    return <p className="text-sm text-gray-400 py-4 text-center">No epoch data yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 cursor-pointer select-none hover:text-gray-700"
              >
                <span className="inline-flex items-center gap-1">
                  {col.label}
                  {sortKey === col.key && (
                    <span className="text-brand-600">{sortDir === "asc" ? "\u2191" : "\u2193"}</span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {sorted.map((row) => {
            const isBest = bestEpoch !== undefined && row.epoch_number === bestEpoch;
            return (
              <tr
                key={row.epoch_number}
                className={
                  isBest
                    ? "bg-green-50 font-medium"
                    : "hover:bg-gray-50 transition-colors"
                }
              >
                {COLUMNS.map((col) => (
                  <td key={col.key} className="px-4 py-2 whitespace-nowrap text-gray-900">
                    {col.format(row[col.key])}
                    {isBest && col.key === "epoch_number" && (
                      <span className="ml-1.5 inline-flex items-center rounded-full bg-green-100 px-1.5 py-0.5 text-[10px] font-semibold text-green-700">
                        Best
                      </span>
                    )}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
