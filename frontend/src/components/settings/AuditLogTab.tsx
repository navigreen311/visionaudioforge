'use client';

import { API_BASE_URL } from "@/lib/api";

import React from 'react';
import Badge from '../ui/Badge';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuditLogEntry {
  id: string;
  timestamp: string;
  user_name: string;
  user_avatar: string;
  action: string;
  resource: string;
  details: Record<string, string | number | boolean | null>;
  ip_address: string;
}

interface AuditLogResponse {
  entries: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

type ActionFilter = '' | 'Create' | 'Update' | 'Delete' | 'Login' | 'Export' | 'Install';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ACTION_OPTIONS: { label: string; value: ActionFilter }[] = [
  { label: 'All Actions', value: '' },
  { label: 'Create', value: 'Create' },
  { label: 'Update', value: 'Update' },
  { label: 'Delete', value: 'Delete' },
  { label: 'Login', value: 'Login' },
  { label: 'Export', value: 'Export' },
  { label: 'Install', value: 'Install' },
];

const ACTION_BADGE_VARIANT: Record<string, string> = {
  Create: 'success',
  Delete: 'danger',
  Update: 'info',
  Login: 'neutral',
  Export: 'warning',
  Install: 'warning',
};

const PAGE_SIZE = 25;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function buildCsvContent(entries: AuditLogEntry[]): string {
  const header = 'Timestamp,User,Action,Resource,IP Address,Details';
  const rows = entries.map((e) => {
    const detailStr = JSON.stringify(e.details).replace(/"/g, '""');
    return `"${e.timestamp}","${e.user_name}","${e.action}","${e.resource}","${e.ip_address}","${detailStr}"`;
  });
  return [header, ...rows].join('\n');
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AuditLogTab() {
  const [entries, setEntries] = React.useState<AuditLogEntry[]>([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(true);

  // Filters
  const [search, setSearch] = React.useState('');
  const [userFilter, setUserFilter] = React.useState('');
  const [actionFilter, setActionFilter] = React.useState<ActionFilter>('');
  const [dateFrom, setDateFrom] = React.useState('');
  const [dateTo, setDateTo] = React.useState('');

  // Expanded row
  const [expandedId, setExpandedId] = React.useState<string | null>(null);

  // Unique users for dropdown (collected from all fetched entries)
  const [knownUsers, setKnownUsers] = React.useState<string[]>([]);

  // Fetch audit log
  const fetchLog = React.useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('page_size', String(PAGE_SIZE));
      if (search) params.set('search', search);
      if (userFilter) params.set('user', userFilter);
      if (actionFilter) params.set('action', actionFilter);
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);

      const baseUrl = API_BASE_URL;
      const res = await fetch(`${baseUrl}/api/settings/audit-log?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: AuditLogResponse = await res.json();
      setEntries(data.entries);
      setTotal(data.total);

      // Collect unique user names
      const names = data.entries.map((e) => e.user_name);
      setKnownUsers((prev) => {
        const merged = new Set([...prev, ...names]);
        return Array.from(merged).sort();
      });
    } catch {
      setEntries([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, search, userFilter, actionFilter, dateFrom, dateTo]);

  React.useEffect(() => {
    void fetchLog();
  }, [fetchLog]);

  // Reset page when filters change
  React.useEffect(() => {
    setPage(1);
  }, [search, userFilter, actionFilter, dateFrom, dateTo]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // CSV export
  const handleExport = () => {
    const csv = buildCsvContent(entries);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* ---- Filter Bar ---- */}
      <div className="flex flex-wrap items-end gap-3">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">Search</label>
          <input
            type="text"
            placeholder="Search resources & details..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* User dropdown */}
        <div className="min-w-[160px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">User</label>
          <select
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm bg-white focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="">All Users</option>
            {knownUsers.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </select>
        </div>

        {/* Action dropdown */}
        <div className="min-w-[140px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">Action</label>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value as ActionFilter)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm bg-white focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            {ACTION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date from */}
        <div className="min-w-[150px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* Date to */}
        <div className="min-w-[150px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* Export button */}
        <button
          onClick={handleExport}
          disabled={entries.length === 0}
          className="rounded bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          Export Log
        </button>
      </div>

      {/* ---- Table ---- */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Timestamp
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                User
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Action
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Resource
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Details
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                IP
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  Loading audit log...
                </td>
              </tr>
            ) : entries.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  No audit log entries found.
                </td>
              </tr>
            ) : (
              entries.map((entry) => {
                const isExpanded = expandedId === entry.id;
                return (
                  <React.Fragment key={entry.id}>
                    <tr
                      onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                      className="cursor-pointer hover:bg-gray-50 transition-colors"
                    >
                      {/* Timestamp */}
                      <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
                        <div>{formatTimestamp(entry.timestamp)}</div>
                        <div className="text-xs text-gray-400">{relativeTime(entry.timestamp)}</div>
                      </td>

                      {/* User */}
                      <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">
                            {entry.user_avatar}
                          </span>
                          <span>{entry.user_name}</span>
                        </div>
                      </td>

                      {/* Action badge */}
                      <td className="px-4 py-3 text-sm whitespace-nowrap">
                        <Badge variant={ACTION_BADGE_VARIANT[entry.action] ?? 'neutral'}>
                          {entry.action}
                        </Badge>
                      </td>

                      {/* Resource */}
                      <td className="px-4 py-3 text-sm text-gray-900 max-w-[260px] truncate">
                        {entry.resource}
                      </td>

                      {/* Details preview */}
                      <td className="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate font-mono text-xs">
                        {JSON.stringify(entry.details).slice(0, 60)}
                        {JSON.stringify(entry.details).length > 60 ? '...' : ''}
                      </td>

                      {/* IP (masked) */}
                      <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap font-mono text-xs">
                        {entry.ip_address}
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {isExpanded && (
                      <tr className="bg-gray-50">
                        <td colSpan={6} className="px-6 py-4">
                          <div className="text-xs font-medium text-gray-500 mb-2">Full Payload</div>
                          <pre className="rounded bg-gray-900 p-4 text-xs text-green-300 font-mono overflow-x-auto whitespace-pre-wrap">
                            {JSON.stringify(entry, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ---- Pagination ---- */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-gray-200 pt-3">
          <span className="text-sm text-gray-700">
            Page {page} of {totalPages} ({total} entries)
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50 hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
