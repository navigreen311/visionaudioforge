'use client';

import React, { useState, useCallback } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ErrorTrend {
  /** 7 data points representing counts over the last 7 intervals. */
  values: [number, number, number, number, number, number, number];
}

export interface ErrorDetail {
  traceIds: string[];
  stackExcerpt: string;
}

export interface ErrorRow {
  id: string;
  errorType: string;
  count: number;
  lastSeen: string; // ISO timestamp
  trend: ErrorTrend;
  affectedEndpoints: string[];
  detail: ErrorDetail;
}

export interface ErrorTaxonomyTableProps {
  data: ErrorRow[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
// Sparkline SVG (7-point)
// ---------------------------------------------------------------------------

function Sparkline({ values }: { values: number[] }) {
  const width = 56;
  const height = 20;
  const padding = 2;

  const max = Math.max(...values, 1);
  const points = values.map((v, i) => {
    const x = padding + (i / (values.length - 1)) * (width - 2 * padding);
    const y = height - padding - (v / max) * (height - 2 * padding);
    return `${x},${y}`;
  });

  const last = values[values.length - 1];
  const prev = values[values.length - 2];
  const strokeColor = last > prev ? '#ef4444' : last < prev ? '#22c55e' : '#6b7280';

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="inline-block">
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Expanded detail row
// ---------------------------------------------------------------------------

function DetailPanel({ detail }: { detail: ErrorDetail }) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = useCallback((traceId: string) => {
    navigator.clipboard.writeText(traceId).then(() => {
      setCopiedId(traceId);
      setTimeout(() => setCopiedId(null), 1500);
    });
  }, []);

  return (
    <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
      {/* Trace IDs */}
      <div className="mb-2">
        <span className="text-xs font-semibold uppercase text-gray-500">Trace IDs</span>
        <div className="mt-1 flex flex-wrap gap-2">
          {detail.traceIds.map((tid) => (
            <span
              key={tid}
              className="inline-flex items-center gap-1 rounded bg-gray-200 px-2 py-0.5 text-xs font-mono text-gray-700"
            >
              {tid.length > 16 ? `${tid.slice(0, 8)}...${tid.slice(-4)}` : tid}
              <button
                type="button"
                onClick={() => handleCopy(tid)}
                className="ml-1 text-gray-400 hover:text-gray-700"
                title="Copy trace ID"
              >
                {copiedId === tid ? (
                  <svg className="h-3.5 w-3.5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                )}
              </button>
            </span>
          ))}
        </div>
      </div>

      {/* Stack trace excerpt */}
      <div>
        <span className="text-xs font-semibold uppercase text-gray-500">Stack Trace</span>
        <pre className="mt-1 max-h-32 overflow-auto rounded bg-gray-900 p-3 text-xs text-green-400 font-mono leading-relaxed">
          {detail.stackExcerpt}
        </pre>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ErrorTaxonomyTable({ data }: ErrorTaxonomyTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleRow = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  return (
    <div className="overflow-auto rounded-lg border border-gray-200 bg-white shadow-sm" style={{ maxHeight: 300 }}>
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50 sticky top-0 z-10">
          <tr>
            {['Error Type', 'Count', 'Last Seen', 'Trend', 'Affected Endpoints'].map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.length === 0 ? (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                No error data available.
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <React.Fragment key={row.id}>
                <tr
                  onClick={() => toggleRow(row.id)}
                  className="cursor-pointer hover:bg-gray-50 transition-colors"
                >
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-gray-900">
                    <div className="flex items-center gap-2">
                      <svg
                        className={`h-3.5 w-3.5 shrink-0 text-gray-400 transition-transform ${
                          expandedId === row.id ? 'rotate-90' : ''
                        }`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                      <code className="text-xs">{row.errorType}</code>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums text-gray-700">
                    {row.count.toLocaleString()}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                    {formatRelative(row.lastSeen)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <Sparkline values={row.trend.values} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {row.affectedEndpoints.map((ep) => (
                        <span
                          key={ep}
                          className="inline-block rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 font-mono"
                        >
                          {ep}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
                {expandedId === row.id && (
                  <tr>
                    <td colSpan={5} className="p-0">
                      <DetailPanel detail={row.detail} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
