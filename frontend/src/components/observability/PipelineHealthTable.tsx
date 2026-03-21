'use client';

import React, { useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type PipelineStatus = 'running' | 'healthy' | 'degraded' | 'failed' | 'inactive';

export interface PipelineRow {
  id: string;
  name: string;
  status: PipelineStatus;
  runs24h: number;
  successRate: number; // 0-1
  avgDurationMs: number;
  lastRun: string; // ISO timestamp
  enabled: boolean;
}

export interface PipelineHealthTableProps {
  data: PipelineRow[];
  onToggleEnabled?: (id: string, enabled: boolean) => void;
  onViewRuns?: (id: string) => void;
}

// ---------------------------------------------------------------------------
// Status badge config
// ---------------------------------------------------------------------------

const statusConfig: Record<PipelineStatus, { label: string; dot: string; bg: string; text: string; pulse?: boolean }> = {
  running:  { label: 'Running',  dot: 'bg-blue-500',   bg: 'bg-blue-100',   text: 'text-blue-800',  pulse: true },
  healthy:  { label: 'Healthy',  dot: 'bg-green-500',  bg: 'bg-green-100',  text: 'text-green-800' },
  degraded: { label: 'Degraded', dot: 'bg-amber-500',  bg: 'bg-amber-100',  text: 'text-amber-800' },
  failed:   { label: 'Failed',   dot: 'bg-red-500',    bg: 'bg-red-100',    text: 'text-red-800' },
  inactive: { label: 'Inactive', dot: 'bg-gray-400',   bg: 'bg-gray-100',   text: 'text-gray-600' },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 0) return 'just now';
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: PipelineStatus }) {
  const cfg = statusConfig[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.text}`}>
      <span className="relative flex h-2 w-2">
        {cfg.pulse && (
          <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${cfg.dot} opacity-75`} />
        )}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${cfg.dot}`} />
      </span>
      {cfg.label}
    </span>
  );
}

function SuccessBar({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100);
  const barColor = pct >= 95 ? 'bg-green-500' : pct >= 80 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-20 rounded-full bg-gray-200 overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-600 tabular-nums">{pct}%</span>
    </div>
  );
}

function ToggleSwitch({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
        checked ? 'bg-blue-600' : 'bg-gray-300'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow ring-0 transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function PipelineHealthTable({
  data,
  onToggleEnabled,
  onViewRuns,
}: PipelineHealthTableProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-4">
      {/* Toggle button */}
      <button
        type="button"
        onClick={() => setExpanded((p) => !p)}
        className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
      >
        <svg
          className={`h-4 w-4 transition-transform ${expanded ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        View per-pipeline breakdown
      </button>

      {/* Expandable table */}
      {expanded && (
        <div className="mt-3 overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {['Pipeline Name', 'Status', 'Runs (24h)', 'Success Rate', 'Avg Duration', 'Last Run', 'Actions'].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    No pipeline data available.
                  </td>
                </tr>
              ) : (
                data.map((row) => (
                  <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                    <td className="whitespace-nowrap px-4 py-3 font-medium text-gray-900">
                      {row.name}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <StatusBadge status={row.status} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums text-gray-700">
                      {row.runs24h.toLocaleString()}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <SuccessBar rate={row.successRate} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums text-gray-700">
                      {formatDuration(row.avgDurationMs)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                      {formatRelative(row.lastRun)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => onViewRuns?.(row.id)}
                          className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
                        >
                          View runs
                        </button>
                        <ToggleSwitch
                          checked={row.enabled}
                          onChange={(v) => onToggleEnabled?.(row.id, v)}
                        />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
