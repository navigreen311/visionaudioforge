"use client";

import React, { useState, useCallback, useMemo } from "react";
import type { RoundData, RoundStatus } from "./types";

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface RoundHistoryTableProps {
  rounds: RoundData[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const STATUS_STYLES: Record<RoundStatus, { bg: string; text: string; label: string }> = {
  complete: { bg: "bg-green-100", text: "text-green-800", label: "Complete" },
  partial: { bg: "bg-amber-100", text: "text-amber-800", label: "Partial" },
  failed: { bg: "bg-red-100", text: "text-red-800", label: "Failed" },
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s.toFixed(0)}s`;
}

function roundsToCsv(rounds: RoundData[]): string {
  const header = "Round,Participants,Accuracy,Loss,Epsilon Spent,Duration (s),Status";
  const rows = rounds.map((r) =>
    [r.round, r.participants, r.accuracy.toFixed(4), r.loss.toFixed(4), r.epsilonSpent.toFixed(4), r.durationSeconds.toFixed(1), r.status].join(","),
  );
  return [header, ...rows].join("\n");
}

function downloadCsv(content: string, filename: string): void {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function RoundHistoryTable({ rounds }: RoundHistoryTableProps) {
  const [open, setOpen] = useState(false);
  const [expandedRound, setExpandedRound] = useState<number | null>(null);

  const lastRound = useMemo(() => {
    if (rounds.length === 0) return -1;
    return Math.max(...rounds.map((r) => r.round));
  }, [rounds]);

  const toggleExpand = useCallback((round: number) => {
    setExpandedRound((prev) => (prev === round ? null : round));
  }, []);

  const handleExport = useCallback(() => {
    downloadCsv(roundsToCsv(rounds), "round-history.csv");
  }, [rounds]);

  if (rounds.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-4 text-center">
        No round history yet.
      </p>
    );
  }

  return (
    <div className="rounded-lg border">
      {/* Toggle header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <span className="inline-flex items-center gap-2">
          <span
            className={`inline-block transition-transform ${open ? "rotate-90" : ""}`}
          >
            &#9654;
          </span>
          Show round history ({rounds.length} rounds)
        </span>
        {open && (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              handleExport();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.stopPropagation();
                handleExport();
              }
            }}
            className="text-xs font-medium text-brand-600 hover:text-brand-700 px-2 py-1 rounded hover:bg-brand-50 transition-colors"
          >
            Export CSV
          </span>
        )}
      </button>

      {/* Table content */}
      {open && (
        <div className="overflow-x-auto border-t">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 w-8" />
                <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Round</th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Participants</th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Accuracy</th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Loss</th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Privacy &epsilon; Spent</th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Duration</th>
                <th className="px-4 py-2 text-center text-xs font-medium uppercase tracking-wider text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {rounds.map((r) => {
                const isLast = r.round === lastRound;
                const isExpanded = expandedRound === r.round;
                const style = STATUS_STYLES[r.status];

                return (
                  <React.Fragment key={r.round}>
                    {/* Main row */}
                    <tr
                      onClick={() => toggleExpand(r.round)}
                      className={`cursor-pointer transition-colors ${
                        isLast
                          ? "bg-blue-50 font-medium"
                          : "hover:bg-gray-50"
                      }`}
                    >
                      <td className="px-4 py-2 text-gray-400">
                        <span
                          className={`inline-block text-[10px] transition-transform ${isExpanded ? "rotate-90" : ""}`}
                        >
                          &#9654;
                        </span>
                      </td>
                      <td className="px-4 py-2 whitespace-nowrap text-gray-900">
                        {r.round}
                        {isLast && (
                          <span className="ml-1.5 inline-flex items-center rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">
                            Latest
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-gray-900">{r.participants}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-gray-900">{(r.accuracy * 100).toFixed(1)}%</td>
                      <td className="px-4 py-2 text-right tabular-nums text-gray-900">{r.loss.toFixed(4)}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-gray-900">{r.epsilonSpent.toFixed(4)}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-gray-900">{formatDuration(r.durationSeconds)}</td>
                      <td className="px-4 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
                          {style.label}
                        </span>
                      </td>
                    </tr>

                    {/* Expanded sub-rows: site updates */}
                    {isExpanded && r.siteUpdates.length > 0 && (
                      <tr>
                        <td colSpan={8} className="px-0 py-0">
                          <div className="bg-gray-50 px-8 py-3">
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                              Participating Sites &mdash; Round {r.round}
                            </p>
                            <table className="min-w-full text-xs">
                              <thead>
                                <tr className="text-gray-400">
                                  <th className="text-left py-1 pr-4 font-medium">Site</th>
                                  <th className="text-right py-1 pr-4 font-medium">Samples</th>
                                  <th className="text-right py-1 pr-4 font-medium">Local Loss</th>
                                  <th className="text-right py-1 pr-4 font-medium">Local Accuracy</th>
                                  <th className="text-right py-1 font-medium">Upload Time</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-gray-200">
                                {r.siteUpdates.map((su) => (
                                  <tr key={su.siteId} className="text-gray-700">
                                    <td className="py-1.5 pr-4 font-mono">{su.siteId}</td>
                                    <td className="py-1.5 pr-4 text-right tabular-nums">{su.samplesUsed.toLocaleString()}</td>
                                    <td className="py-1.5 pr-4 text-right tabular-nums">{su.localLoss.toFixed(4)}</td>
                                    <td className="py-1.5 pr-4 text-right tabular-nums">{(su.localAccuracy * 100).toFixed(1)}%</td>
                                    <td className="py-1.5 text-right tabular-nums">{su.uploadDuration.toFixed(1)}s</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
