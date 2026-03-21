'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Frequency = 'hourly' | 'daily' | 'weekly' | 'custom';
type Weekday = 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';

const WEEKDAYS: Weekday[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const WEEKDAY_CRON: Record<Weekday, string> = {
  Mon: '1', Tue: '2', Wed: '3', Thu: '4', Fri: '5', Sat: '6', Sun: '0',
};

const COMMON_TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
];

interface ScheduleModalProps {
  pipelineId: string;
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function cronToHumanReadable(cron: string): string {
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return 'Invalid cron expression';

  const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;

  if (dayOfWeek !== '*' && dayOfMonth === '*' && month === '*') {
    const days = dayOfWeek.split(',').map((d) => {
      const entry = Object.entries(WEEKDAY_CRON).find(([, v]) => v === d);
      return entry ? entry[0] : d;
    });
    return `Every ${days.join(', ')} at ${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
  }
  if (hour === '*' && dayOfMonth === '*' && month === '*' && dayOfWeek === '*') {
    return `Every hour at minute ${minute}`;
  }
  if (dayOfMonth === '*' && month === '*' && dayOfWeek === '*') {
    return `Daily at ${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
  }
  return cron;
}

function computeNextRuns(cron: string, timezone: string, count = 3): string[] {
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return [];

  const [minuteStr, hourStr, , , dowStr] = parts;
  const results: string[] = [];
  const now = new Date();
  const cursor = new Date(now);

  for (let i = 0; i < 365 && results.length < count; i++) {
    cursor.setDate(cursor.getDate() + (i === 0 ? 0 : 1));

    const hours = hourStr === '*'
      ? Array.from({ length: 24 }, (_, h) => h)
      : hourStr.includes('/')
        ? Array.from({ length: Math.ceil(24 / Number(hourStr.split('/')[1])) }, (_, h) => h * Number(hourStr.split('/')[1]))
        : [Number(hourStr)];
    const minutes = [Number(minuteStr)];

    for (const h of hours) {
      for (const m of minutes) {
        const candidate = new Date(cursor);
        candidate.setHours(h, m, 0, 0);

        if (candidate <= now) continue;

        if (dowStr !== '*') {
          const allowedDays = dowStr.split(',').map(Number);
          if (!allowedDays.includes(candidate.getDay())) continue;
        }

        results.push(
          candidate.toLocaleString('en-US', {
            timeZone: timezone,
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          }),
        );
        if (results.length >= count) break;
      }
      if (results.length >= count) break;
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ScheduleModal({ pipelineId, open, onClose, onSaved }: ScheduleModalProps) {
  const [enabled, setEnabled] = useState(true);
  const [frequency, setFrequency] = useState<Frequency>('daily');
  const [everyXHours, setEveryXHours] = useState(1);
  const [dailyTime, setDailyTime] = useState('09:00');
  const [weeklyDays, setWeeklyDays] = useState<Weekday[]>(['Mon']);
  const [weeklyTime, setWeeklyTime] = useState('09:00');
  const [customCron, setCustomCron] = useState('0 9 * * *');
  const [timezone, setTimezone] = useState('UTC');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Build cron from UI state
  const cron = useMemo((): string => {
    switch (frequency) {
      case 'hourly':
        return `0 */${everyXHours} * * *`;
      case 'daily': {
        const [h, m] = dailyTime.split(':').map(Number);
        return `${m} ${h} * * *`;
      }
      case 'weekly': {
        const [h, m] = weeklyTime.split(':').map(Number);
        const days = weeklyDays.map((d) => WEEKDAY_CRON[d]).join(',');
        return `${m} ${h} * * ${days || '*'}`;
      }
      case 'custom':
        return customCron;
    }
  }, [frequency, everyXHours, dailyTime, weeklyDays, weeklyTime, customCron]);

  const humanReadable = useMemo(() => cronToHumanReadable(cron), [cron]);
  const nextRuns = useMemo(() => computeNextRuns(cron, timezone), [cron, timezone]);

  const toggleWeekday = useCallback((day: Weekday) => {
    setWeeklyDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day],
    );
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const resp = await fetch(`/api/pipeline/${pipelineId}/schedule`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled, cron, timezone }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({ detail: 'Unknown error' }));
        setError(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
      } else {
        onSaved?.();
        onClose();
      }
    } catch {
      setError('Network error — could not save schedule');
    } finally {
      setSaving(false);
    }
  };

  // Reset state when opening
  useEffect(() => {
    if (open) {
      setError(null);
      setSaving(false);
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold text-gray-800 mb-5">Schedule Pipeline</h3>

        {/* Enable toggle */}
        <div className="flex items-center justify-between mb-5">
          <span className="text-sm font-medium text-gray-700">Enable schedule</span>
          <button
            type="button"
            role="switch"
            aria-checked={enabled}
            onClick={() => setEnabled((v) => !v)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              enabled ? 'bg-blue-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                enabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Frequency buttons */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-2">Frequency</label>
          <div className="flex gap-2">
            {(['hourly', 'daily', 'weekly', 'custom'] as Frequency[]).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFrequency(f)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  frequency === f
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Frequency-specific controls */}
        <div className="mb-5 space-y-4">
          {frequency === 'hourly' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Every X hours
              </label>
              <input
                type="number"
                min={1}
                max={23}
                value={everyXHours}
                onChange={(e) => setEveryXHours(Math.max(1, Math.min(23, Number(e.target.value))))}
                className="w-24 border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
          )}

          {frequency === 'daily' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Time</label>
              <input
                type="time"
                value={dailyTime}
                onChange={(e) => setDailyTime(e.target.value)}
                className="w-40 border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
          )}

          {frequency === 'weekly' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Days</label>
                <div className="flex gap-1.5 flex-wrap">
                  {WEEKDAYS.map((day) => (
                    <button
                      key={day}
                      type="button"
                      onClick={() => toggleWeekday(day)}
                      className={`px-2.5 py-1 text-xs font-medium rounded transition-colors ${
                        weeklyDays.includes(day)
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {day}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Time</label>
                <input
                  type="time"
                  value={weeklyTime}
                  onChange={(e) => setWeeklyTime(e.target.value)}
                  className="w-40 border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
              </div>
            </>
          )}

          {frequency === 'custom' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cron expression
              </label>
              <input
                type="text"
                value={customCron}
                onChange={(e) => setCustomCron(e.target.value)}
                placeholder="0 9 * * *"
                className="w-full border border-gray-300 rounded-lg p-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <p className="mt-1 text-xs text-gray-400">
                Format: minute hour day-of-month month day-of-week
              </p>
            </div>
          )}
        </div>

        {/* Human-readable preview */}
        <div className="mb-4 bg-gray-50 rounded-lg p-3">
          <span className="text-xs text-gray-500">Schedule: </span>
          <span className="text-sm font-medium text-gray-700">{humanReadable}</span>
        </div>

        {/* Timezone */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
          <select
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            {COMMON_TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>
                {tz.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>

        {/* Next 3 runs */}
        {nextRuns.length > 0 && (
          <div className="mb-5">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Next 3 runs
            </h4>
            <ul className="space-y-1">
              {nextRuns.map((run, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
                  {run}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-2">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50 transition-colors"
          >
            {saving ? 'Saving...' : 'Save Schedule'}
          </button>
        </div>
      </div>
    </div>
  );
}
