"use client";

import { useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ParticipantStatus = "active" | "idle" | "disconnected";

export interface FLParticipant {
  id: string;
  name: string;
  status: ParticipantStatus;
  samples: number;
  contributionPct: number;
  localAccuracy: number;
  dataQuality: number;
  location?: string;
  connectionUrl?: string;
}

interface ParticipantTableProps {
  federationId: string;
  participants: FLParticipant[];
  onAddParticipant?: () => void;
  onRetry?: (siteId: string) => void;
  onRemove?: (siteId: string) => void;
  onViewLogs?: (siteId: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_BADGE: Record<ParticipantStatus, string> = {
  active: "bg-green-100 text-green-800",
  idle: "bg-amber-100 text-amber-800",
  disconnected: "bg-red-100 text-red-800",
};

const STATUS_DOT: Record<ParticipantStatus, string> = {
  active: "bg-green-500",
  idle: "bg-amber-500",
  disconnected: "bg-red-500",
};

const ROW_BG: Record<ParticipantStatus, string> = {
  active: "",
  idle: "bg-amber-50/50",
  disconnected: "bg-red-50/50",
};

function ContributionBar({ pct }: { pct: number }) {
  const clamped = Math.min(Math.max(pct, 0), 100);
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-600 rounded-full transition-all"
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-gray-600">
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

function QualityIndicator({ score }: { score: number }) {
  const color =
    score >= 0.9
      ? "text-green-600"
      : score >= 0.7
        ? "text-amber-600"
        : "text-red-600";
  return (
    <span className={`text-sm font-medium tabular-nums ${color}`}>
      {(score * 100).toFixed(0)}%
    </span>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ParticipantTable({
  federationId,
  participants,
  onAddParticipant,
  onRetry,
  onRemove,
  onViewLogs,
}: ParticipantTableProps) {
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null);

  const handleRemove = (siteId: string) => {
    if (confirmRemove === siteId) {
      onRemove?.(siteId);
      setConfirmRemove(null);
    } else {
      setConfirmRemove(siteId);
    }
  };

  // Reset confirm state when mouse leaves
  const handleMouseLeave = (siteId: string) => {
    setHoveredRow(null);
    if (confirmRemove === siteId) {
      setConfirmRemove(null);
    }
  };

  return (
    <div className="rounded-lg border overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between bg-gray-50 px-4 py-3 border-b">
        <h3 className="text-sm font-semibold text-gray-700">
          Participants{" "}
          <span className="text-gray-400 font-normal">
            ({participants.length})
          </span>
        </h3>
        {onAddParticipant && (
          <button
            onClick={onAddParticipant}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 transition-colors"
          >
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4v16m8-8H4"
              />
            </svg>
            Add Participant
          </button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50/80">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-gray-500 text-xs uppercase tracking-wider">
                Site Name
              </th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-500 text-xs uppercase tracking-wider">
                Status
              </th>
              <th className="text-right px-4 py-2.5 font-medium text-gray-500 text-xs uppercase tracking-wider">
                Samples
              </th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-500 text-xs uppercase tracking-wider">
                Contribution
              </th>
              <th className="text-right px-4 py-2.5 font-medium text-gray-500 text-xs uppercase tracking-wider">
                Local Acc.
              </th>
              <th className="text-right px-4 py-2.5 font-medium text-gray-500 text-xs uppercase tracking-wider">
                Data Quality
              </th>
              <th className="text-right px-4 py-2.5 font-medium text-gray-500 text-xs uppercase tracking-wider w-32">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {participants.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-8 text-center text-sm text-gray-400"
                >
                  No participants yet. Click &quot;Add Participant&quot; to
                  invite a site.
                </td>
              </tr>
            )}

            {participants.map((p) => (
              <tr
                key={p.id}
                className={`transition-colors ${ROW_BG[p.status]} ${
                  hoveredRow === p.id ? "bg-gray-50" : ""
                }`}
                onMouseEnter={() => setHoveredRow(p.id)}
                onMouseLeave={() => handleMouseLeave(p.id)}
              >
                {/* Site Name */}
                <td className="px-4 py-2.5">
                  <div>
                    <p className="font-medium text-gray-900">{p.name}</p>
                    <p className="text-xs text-gray-400 font-mono">{p.id}</p>
                  </div>
                </td>

                {/* Status */}
                <td className="px-4 py-2.5">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[p.status]}`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[p.status]}`}
                    />
                    {p.status}
                  </span>
                </td>

                {/* Samples */}
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {p.samples.toLocaleString()}
                </td>

                {/* Contribution bar */}
                <td className="px-4 py-2.5">
                  <ContributionBar pct={p.contributionPct} />
                </td>

                {/* Local Accuracy */}
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {(p.localAccuracy * 100).toFixed(1)}%
                </td>

                {/* Data Quality */}
                <td className="px-4 py-2.5 text-right">
                  <QualityIndicator score={p.dataQuality} />
                </td>

                {/* Hover actions */}
                <td className="px-4 py-2.5 text-right">
                  <div
                    className={`flex items-center justify-end gap-1 transition-opacity ${
                      hoveredRow === p.id ? "opacity-100" : "opacity-0"
                    }`}
                  >
                    {/* Retry (only for disconnected) */}
                    {p.status === "disconnected" && (
                      <button
                        onClick={() => onRetry?.(p.id)}
                        title="Retry connection"
                        className="rounded p-1.5 text-gray-400 hover:bg-green-50 hover:text-green-600 transition-colors"
                      >
                        <svg
                          className="h-4 w-4"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={2}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                          />
                        </svg>
                      </button>
                    )}

                    {/* View Logs */}
                    <button
                      onClick={() => onViewLogs?.(p.id)}
                      title="View logs"
                      className="rounded p-1.5 text-gray-400 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                    >
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                    </button>

                    {/* Remove (with confirm) */}
                    <button
                      onClick={() => handleRemove(p.id)}
                      title={
                        confirmRemove === p.id
                          ? "Click again to confirm removal"
                          : "Remove participant"
                      }
                      className={`rounded p-1.5 transition-colors ${
                        confirmRemove === p.id
                          ? "bg-red-100 text-red-600"
                          : "text-gray-400 hover:bg-red-50 hover:text-red-600"
                      }`}
                    >
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Federation ID footer */}
      <div className="bg-gray-50 px-4 py-2 border-t text-xs text-gray-400">
        Federation: <span className="font-mono">{federationId}</span>
      </div>
    </div>
  );
}
