'use client';

import { readWorkspaceId } from "@/lib/session";

import { useState, useEffect, useCallback, useRef } from 'react';
import ShiftScheduleGrid from './ShiftScheduleGrid';

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

type TimeSlotPreset = 'Morning' | 'Afternoon' | 'Night' | 'Custom';

// A shift is a reviewer and a window. `zone`, `slot` and `accuracy` were on
// these types and on no table: zones are not a concept the platform has, the
// slot is derivable from the start time rather than stored, and per-shift
// accuracy needs ground-truth labels nothing records. They were only ever
// populated from the constants at the top of this file.
interface ActiveShift {
  shift_id: string;
  reviewer_name: string;
  reviewer_avatar: string;
  started_at: string;
  tasks_completed: number;
}

interface ShiftHistoryRow {
  shift_id: string;
  reviewer_name: string;
  date: string;
  tasks_completed: number;
  duration_h: number;
}

interface ShiftPayload {
  shift_id: string;
  reviewer_id: string | null;
  reviewer_name: string;
  start_time: string;
  end_time: string;
  active: boolean;
  tasks_completed: number;
  accuracy: number | null;
}

interface CreateShiftForm {
  reviewer_id: string;
  zone: string;
  date: string;
  time_slot: TimeSlotPreset;
  custom_start: string;
  custom_end: string;
}

// ------------------------------------------------------------------
// Constants
// ------------------------------------------------------------------

const API = '/api/reviewops';

// Reviewers and shift history both come from /api/reviewops.
//
// This file used to define five people ("Alice M.", "Brian K."...), one active
// shift and ten history rows with accuracy percentages, and seed its state with
// them. It did call /shifts - but only overwrote the fakes when the response
// happened to contain matching rows, so an empty queue displayed ten invented
// shifts, and a real row would have thrown: the payload had no `reviewer_name`
// and this read `.split(' ')` off it.

// ------------------------------------------------------------------
// Elapsed Timer Hook
// ------------------------------------------------------------------

function useElapsedTimer(startedAt: string): string {
  const [elapsed, setElapsed] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const update = () => {
      const diff = Date.now() - new Date(startedAt).getTime();
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setElapsed(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`);
    };
    update();
    intervalRef.current = setInterval(update, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [startedAt]);

  return elapsed;
}

// ------------------------------------------------------------------
// Active Shift Panel
// ------------------------------------------------------------------

function ActiveShiftPanel({ shift, onEnd }: { shift: ActiveShift; onEnd: () => void }) {
  const elapsed = useElapsedTimer(shift.started_at);

  return (
    <div className="rounded-xl border border-green-200 bg-green-50/60 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-brand-600 text-white text-sm font-bold flex items-center justify-center">
            {shift.reviewer_avatar}
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">{shift.reviewer_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
          </span>
          <span className="text-xs font-medium text-green-700">Active</span>
        </div>
      </div>

      {/* "Remaining" and "Accuracy" were here. Neither exists: a shift carries
          no task quota to count down from, and per-shift accuracy needs
          ground-truth labels nothing records. Both were read from the invented
          constants this file used to define. */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-gray-500">Elapsed</p>
          <p className="text-lg font-mono font-bold text-gray-900">{elapsed}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-gray-500">Tasks Done</p>
          <p className="text-lg font-bold text-gray-900">{shift.tasks_completed}</p>
        </div>
      </div>

      <button
        onClick={onEnd}
        className="rounded-lg bg-red-600 px-5 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
      >
        End Shift
      </button>
    </div>
  );
}

// ------------------------------------------------------------------
// Create Shift Modal
// ------------------------------------------------------------------

interface CreateShiftModalProps {
  onSave: (form: CreateShiftForm) => void;
  onClose: () => void;
  /** From /api/reviewops/reviewers - people who actually hold review tasks. */
  reviewers: { id: string; name: string }[];
}

function CreateShiftModal({ onSave, onClose, reviewers }: CreateShiftModalProps) {
  const [form, setForm] = useState<CreateShiftForm>({
    reviewer_id: '',
    zone: 'Zone A',
    date: new Date().toISOString().slice(0, 10),
    time_slot: 'Morning',
    custom_start: '',
    custom_end: '',
  });

  const update = <K extends keyof CreateShiftForm>(key: K, value: CreateShiftForm[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const canSave =
    form.reviewer_id &&
    form.date &&
    (form.time_slot !== 'Custom' || (form.custom_start && form.custom_end));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Create Shift</h3>

        <div className="space-y-4">
          {/* Reviewer dropdown */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Reviewer</label>
            <select
              value={form.reviewer_id}
              onChange={(e) => update('reviewer_id', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select reviewer...</option>
              {reviewers.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          {/* Zone */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Zone</label>
            <select
              value={form.zone}
              onChange={(e) => update('zone', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="Zone A">Zone A</option>
              <option value="Zone B">Zone B</option>
              <option value="Zone C">Zone C</option>
            </select>
          </div>

          {/* Date */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Date</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => update('date', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          {/* Time Slot */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Time Slot</label>
            <div className="grid grid-cols-4 gap-2">
              {(['Morning', 'Afternoon', 'Night', 'Custom'] as TimeSlotPreset[]).map((slot) => (
                <button
                  key={slot}
                  type="button"
                  onClick={() => update('time_slot', slot)}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                    form.time_slot === slot
                      ? 'border-brand-600 bg-brand-50 text-brand-700'
                      : 'border-gray-300 text-gray-600 hover:border-gray-400'
                  }`}
                >
                  {slot}
                </button>
              ))}
            </div>
          </div>

          {/* Custom time inputs */}
          {form.time_slot === 'Custom' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Start Time</label>
                <input
                  type="time"
                  value={form.custom_start}
                  onChange={(e) => update('custom_start', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">End Time</label>
                <input
                  type="time"
                  value={form.custom_end}
                  onChange={(e) => update('custom_end', e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (canSave) onSave(form);
            }}
            disabled={!canSave}
            className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Shift History Table
// ------------------------------------------------------------------

function ShiftHistoryTable({ rows }: { rows: ShiftHistoryRow[] }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700">Shift History</h3>
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            {/* Zone, Slot and Accuracy columns were removed: the shift table
                stores a reviewer and a window, and nothing else. Their values
                came from the ten invented rows this file used to define. */}
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Reviewer</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Date</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">Tasks</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">Duration</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((r) => (
              <tr key={r.shift_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-800">{r.reviewer_name}</td>
                <td className="px-4 py-3 text-gray-600 font-mono text-xs">{r.date}</td>
                <td className="px-4 py-3 text-right text-gray-600">{r.tasks_completed}</td>
                <td className="px-4 py-3 text-right text-gray-600">{r.duration_h}h</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="text-center py-8 text-gray-400">No shift history</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// ShiftsTab (exported)
// ------------------------------------------------------------------

export default function ShiftsTab() {
  const [activeShift, setActiveShift] = useState<ActiveShift | null>(null);
  const [history, setHistory] = useState<ShiftHistoryRow[]>([]);
  const [reviewers, setReviewers] = useState<{ id: string; name: string }[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchShifts = useCallback(async () => {
    // The mapping below is the payload /api/reviewops/shifts actually returns.
    // The previous one read `zone`, `date` and `time_slot` off it - fields the
    // shift table has never had - and `accuracy`, which needs ground-truth
    // labels nothing records. Those columns are gone rather than filled with
    // numbers nobody measured.
    try {
      const [shiftRes, reviewerRes] = await Promise.all([
        fetch(`${API}/shifts?workspace_id=${readWorkspaceId()}`),
        fetch(`${API}/reviewers?workspace_id=${readWorkspaceId()}`),
      ]);

      if (reviewerRes.ok) {
        const people: { id: string; name: string }[] = await reviewerRes.json();
        setReviewers(people);
      }

      if (shiftRes.ok) {
        const data: ShiftPayload[] = await shiftRes.json();

        const active = data.find((s) => s.active);
        setActiveShift(
          active
            ? {
                shift_id: active.shift_id,
                reviewer_name: active.reviewer_name,
                reviewer_avatar: (active.reviewer_name || "?")
                  .split(/[\s@.]+/)
                  .map((w) => w[0])
                  .join('')
                  .slice(0, 2)
                  .toUpperCase(),
                started_at: active.start_time,
                tasks_completed: active.tasks_completed,
              }
            : null,
        );

        setHistory(
          data
            .filter((s) => !s.active)
            .slice(0, 10)
            .map((s) => ({
              shift_id: s.shift_id,
              reviewer_name: s.reviewer_name,
              date: s.start_time ? s.start_time.slice(0, 10) : '',
              tasks_completed: s.tasks_completed,
              duration_h:
                s.start_time && s.end_time
                  ? Math.round(
                      (new Date(s.end_time).getTime() -
                        new Date(s.start_time).getTime()) /
                        3600000,
                    )
                  : 0,
            })),
        );
      }
    } catch {
      // Leave the lists empty. Showing invented shifts on a failed request is
      // what this component used to do.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchShifts();
  }, [fetchShifts]);

  const handleCreateShift = async (form: CreateShiftForm) => {
    const slotTimes: Record<string, { start: string; end: string }> = {
      Morning: { start: '06:00', end: '14:00' },
      Afternoon: { start: '14:00', end: '22:00' },
      Night: { start: '22:00', end: '06:00' },
    };

    const times =
      form.time_slot === 'Custom'
        ? { start: form.custom_start, end: form.custom_end }
        : slotTimes[form.time_slot];

    try {
      await fetch(`${API}/shifts?workspace_id=${readWorkspaceId()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: form.reviewer_id,
          zone: form.zone,
          date: form.date,
          time_slot: form.time_slot,
          start_time: `${form.date}T${times.start}:00`,
          end_time: `${form.date}T${times.end}:00`,
        }),
      });
      setShowCreateModal(false);
      fetchShifts();
    } catch {
      /* empty */
    }
  };

  const handleEndShift = () => {
    setActiveShift(null);
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-400">Loading shifts...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header with Create button */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700">Shift Management</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
        >
          Create Shift
        </button>
      </div>

      {/* Active Shift Panel */}
      {activeShift ? (
        <ActiveShiftPanel shift={activeShift} onEnd={handleEndShift} />
      ) : (
        <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center">
          <p className="text-sm text-gray-400">No active shift right now</p>
        </div>
      )}

      {/* Schedule Grid */}
      <ShiftScheduleGrid />

      {/* Shift History */}
      <ShiftHistoryTable rows={history} />

      {/* Create Shift Modal */}
      {showCreateModal && (
        <CreateShiftModal
          reviewers={reviewers}
          onSave={handleCreateShift}
          onClose={() => setShowCreateModal(false)}
        />
      )}
    </div>
  );
}
