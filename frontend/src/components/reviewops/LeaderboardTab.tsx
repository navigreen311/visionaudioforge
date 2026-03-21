'use client';

import React, { useCallback, useEffect, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TimeRange = 'today' | 'week' | 'month';

interface TrendPoint {
  day: number;
  value: number;
}

interface ReviewerEntry {
  id: string;
  name: string;
  avatar_url: string;
  tasks_completed: number;
  max_tasks: number;
  accuracy: number;
  avg_review_time_sec: number;
  streak_days: number;
  trend: TrendPoint[];
}

interface LeaderboardResponse {
  range: TimeRange;
  entries: ReviewerEntry[];
  my_stats: ReviewerEntry | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
];

function rankBadge(rank: number): React.ReactNode {
  if (rank === 1) return <span className="text-lg" title="1st place">&#x1F451;</span>;
  if (rank === 2) return <span className="text-lg" title="2nd place">&#x1F948;</span>;
  if (rank === 3) return <span className="text-lg" title="3rd place">&#x1F949;</span>;
  return <span className="font-semibold text-gray-500">{rank}</span>;
}

function rowBorderClass(rank: number): string {
  if (rank === 1) return 'border-l-4 border-l-yellow-400';
  if (rank === 2) return 'border-l-4 border-l-gray-400';
  if (rank === 3) return 'border-l-4 border-l-amber-600';
  return '';
}

function accuracyColor(pct: number): string {
  if (pct >= 95) return 'text-green-600';
  if (pct >= 80) return 'text-yellow-600';
  return 'text-red-600';
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

// ---------------------------------------------------------------------------
// Mini-bar: shows completed / max as a small inline bar
// ---------------------------------------------------------------------------

function MiniBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-gray-900 w-8 text-right">{value}</span>
      <div className="h-2 w-20 rounded-full bg-gray-200">
        <div
          className="h-2 rounded-full bg-blue-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 7-point sparkline SVG
// ---------------------------------------------------------------------------

function Sparkline({ points }: { points: TrendPoint[] }) {
  if (points.length < 2) return null;

  const values = points.map((p) => p.value);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = maxV - minV || 1;

  const width = 80;
  const height = 24;
  const padY = 2;

  const coords = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - padY - ((v - minV) / range) * (height - 2 * padY);
    return { x, y };
  });

  const polyline = coords.map((c) => `${c.x},${c.y}`).join(' ');

  const trending = values[values.length - 1] >= values[0];
  const strokeColor = trending ? '#22c55e' : '#ef4444';

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="inline-block">
      <polyline
        fill="none"
        stroke={strokeColor}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        points={polyline}
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Streak badge
// ---------------------------------------------------------------------------

function StreakBadge({ days }: { days: number }) {
  if (days <= 0) return <span className="text-gray-400 text-sm">--</span>;
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800">
      <span>&#x1F525;</span> {days} day streak
    </span>
  );
}

// ---------------------------------------------------------------------------
// My Stats panel
// ---------------------------------------------------------------------------

function MyStatsPanel({ stats }: { stats: ReviewerEntry }) {
  return (
    <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-5">
      <h3 className="text-sm font-semibold text-blue-900 mb-3">My Stats</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <p className="text-xs text-blue-600 uppercase tracking-wider">Tasks Completed</p>
          <p className="text-xl font-bold text-blue-900">{stats.tasks_completed}</p>
        </div>
        <div>
          <p className="text-xs text-blue-600 uppercase tracking-wider">Accuracy</p>
          <p className={`text-xl font-bold ${accuracyColor(stats.accuracy)}`}>
            {stats.accuracy.toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-blue-600 uppercase tracking-wider">Avg Review Time</p>
          <p className="text-xl font-bold text-blue-900">
            {formatTime(stats.avg_review_time_sec)}
          </p>
        </div>
        <div>
          <p className="text-xs text-blue-600 uppercase tracking-wider">Streak</p>
          <p className="text-xl font-bold text-orange-600">
            {stats.streak_days > 0 ? `${stats.streak_days} days` : '--'}
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function LeaderboardTab() {
  const [range, setRange] = useState<TimeRange>('week');
  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaderboard = useCallback(async (r: TimeRange) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/reviewops/leaderboard?range=${r}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: LeaderboardResponse = await res.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeaderboard(range);
  }, [range, fetchLeaderboard]);

  return (
    <div className="space-y-4">
      {/* Time-range selector */}
      <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        {RANGE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setRange(opt.value)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              range === opt.value
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
        </div>
      )}

      {/* Leaderboard table */}
      {!loading && data && (
        <>
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 w-16">
                    Rank
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Reviewer
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Tasks Completed
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Accuracy
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Avg Review Time
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Streak
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Trend
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {data.entries.map((entry, idx) => {
                  const rank = idx + 1;
                  return (
                    <tr
                      key={entry.id}
                      className={`hover:bg-gray-50 transition-colors ${rowBorderClass(rank)}`}
                    >
                      <td className="px-4 py-3 text-center">{rankBadge(rank)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <img
                            src={entry.avatar_url}
                            alt={entry.name}
                            className="h-8 w-8 rounded-full object-cover"
                          />
                          <span className="text-sm font-medium text-gray-900">{entry.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <MiniBar value={entry.tasks_completed} max={entry.max_tasks} />
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-sm font-semibold ${accuracyColor(entry.accuracy)}`}>
                          {entry.accuracy.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {formatTime(entry.avg_review_time_sec)}
                      </td>
                      <td className="px-4 py-3">
                        <StreakBadge days={entry.streak_days} />
                      </td>
                      <td className="px-4 py-3">
                        <Sparkline points={entry.trend} />
                      </td>
                    </tr>
                  );
                })}
                {data.entries.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                      No leaderboard data for this period.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* My Stats panel */}
          {data.my_stats && <MyStatsPanel stats={data.my_stats} />}
        </>
      )}
    </div>
  );
}
